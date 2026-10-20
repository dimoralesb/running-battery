"""Team-level fatigue and running effort: what can and cannot be read from positions
(PLAN decisions 23–24; claims 35 and 38).

``python -m runningbattery.validate.teams data/synthetic/dev [--json out.json]``

Two checks on natural matches with the hidden truth (the estimator's ``signals.json`` must be in
each match folder):

- **Which team is more tired?** Per match and team (outfield player-seconds): the truth's
  short-term tired share (``tired``), late-match wear (tank below ``late_tank_below``) and tank
  used in the last 15 min, against what the estimator sees: the typical-pro battery deficit,
  the typical-pro chance, metabolic power and high-speed running (all of the match, and the last
  15 min). Reported: how often the home-minus-away difference picks the same team as the truth,
  in all matches and in the half with the clearer truth, and Spearman's ρ of the differences.
- **Slower than his top speed when it mattered?** After each turnover, for every outfield
  player of the team that lost the ball, the peak speed in the next ``WINDOW_S`` seconds as a
  share of his match top speed, against the truth's runs in that window: a hard run skipped (a
  tired player's skipped decision), a hard run made (recovery, covering, close down,
  interception), or neither (no run asked by his role). Reported: the share of each, and the
  area under the curve of low speed for "skipped" against "made", "neither" and both, also for
  the player nearest the ball.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from scipy.stats import mannwhitneyu, spearmanr

from runningbattery.agents.tools import MatchData
from runningbattery.engine import params as EP
from runningbattery.io import SIGNALS, read_signals, read_truth

WINDOW_S = 8.0
LATE_S = 75 * 60.0
HARD = ("recovery_run", "covering", "close_down", "interception")
TRUTH = {"tired": "short-term tired share (pools)", "lowtank": "late-match wear share",
         "tank_late": "tank used, last 15 min"}  # fmt: skip
SEEN = ("deficit", "chance", "power", "hsr", "deficit_late", "power_late")


def _clock(period, t):
    return np.asarray(t) + (np.asarray(period) == 2) * 2700.0


def team_measures(folder: Path) -> dict[str, dict[str, float]]:
    """Truth and estimator means per team for one match."""
    sig, tru = read_signals(folder / SIGNALS), read_truth(folder)
    late_tank = float(tru.settings.get("late_tank_below", 0.75))
    meta = json.loads((folder / "metadata.json").read_text())
    pos = {p["id"]: (t["id"], p["position"]) for t in meta["teams"] for p in t["players"]}
    truth = {pt.player_id: pt.series for pt in tru.players}
    acc: dict[str, dict[str, list]] = {}
    for ps in sig.players:
        team, position = pos[ps.player_id]
        if position == "GK":
            continue
        s, t = ps.series, truth[ps.player_id]
        late, tlate = _clock(s.period, s.t) >= LATE_S, _clock(t.period, t.t) >= LATE_S
        speed, battery, tank = np.array(s.speed), np.array(s.battery), np.array(t.tank)
        d = acc.setdefault(team, {k: [] for k in (*TRUTH, *SEEN)})
        d["tired"].append(np.array(t.tired, float))
        d["lowtank"].append((tank < late_tank).astype(float))
        d["tank_late"].append(1.0 - tank[tlate])
        d["deficit"].append(1.0 - battery)
        d["chance"].append(np.array(s.low_chance))
        d["power"].append(np.array(s.power))
        d["hsr"].append(np.where(speed > EP.HI_SPEED, speed, 0.0))
        d["deficit_late"].append(1.0 - battery[late])
        d["power_late"].append(np.array(s.power)[late])
    return {team: {k: float(np.mean(np.concatenate(v))) if any(len(x) for x in v)
                   else float("nan") for k, v in d.items()} for team, d in acc.items()}  # fmt: skip


def agreement(seen: np.ndarray, truth: np.ndarray) -> dict[str, float]:
    """How often the sign of the estimator's home-minus-away difference matches the truth's."""
    ok = np.isfinite(seen) & np.isfinite(truth)
    seen, truth = seen[ok], truth[ok]
    clear = np.abs(truth) >= np.median(np.abs(truth))
    return {"same_team": float(np.mean(np.sign(seen) == np.sign(truth))),
            "same_team_clear_half": float(np.mean(np.sign(seen[clear]) == np.sign(truth[clear]))),
            "rho": float(spearmanr(seen, truth).statistic), "matches": int(ok.sum())}  # fmt: skip


def auc(positive: np.ndarray, negative: np.ndarray) -> float:
    """Probability that a positive scores higher than a negative (ties count half)."""
    if not len(positive) or not len(negative):
        return float("nan")
    return float(mannwhitneyu(positive, negative).statistic / (len(positive) * len(negative)))


def chase_windows(folder: Path) -> list[tuple[float, bool, bool, int]]:
    """(peak speed / top speed, skipped, made, rank by distance to the ball) per player of the
    team that lost the ball, for each turnover."""
    m, tru = MatchData(folder), read_truth(folder)
    runs: dict[str, list] = {}
    for r in tru.runs:
        runs.setdefault(r.player_id, []).append(r)
    rows, seen = [], set()
    for e in m.events:
        if e.phase is None or e.phase.value != "positive_transition" or e.possession_id in seen:
            continue
        seen.add(e.possession_id)
        lost = "away" if e.team_id == "home" else "home"
        k = m.second(e.period, e.t)
        ball = m.ball[e.period][k]
        dist = {}
        for pid, info in m.players.items():
            xy = m.xy[e.period][k, m.col[pid]]
            if info["team"] == lost and info["position"] != "GK" and not np.isnan(xy[0]):
                dist[pid] = float(np.hypot(*(xy - ball)))
        order = sorted(dist, key=dist.get)
        for pid in order:
            s = m.series.get(pid)
            if s is None:
                continue
            speed = s.cols["speed"]
            w = (s.period == e.period) & (s.t > e.t) & (s.t <= e.t + WINDOW_S)
            if w.sum() < WINDOW_S / 2:
                continue
            top = speed[speed < 11.0].max()
            mine = [r for r in runs.get(pid, []) if r.period == e.period
                    and e.t - 1.0 <= r.t_start <= e.t + WINDOW_S]  # fmt: skip
            skipped = any(not r.executed for r in mine)
            made = any(r.executed and r.purpose.value in HARD for r in mine)
            rows.append((float(speed[w].max() / top), skipped, made, order.index(pid)))
    return rows


def chase_summary(rows: list[tuple[float, bool, bool, int]]) -> dict:
    r = np.array([x[0] for x in rows])
    sk = np.array([x[1] for x in rows])
    made = np.array([x[2] for x in rows]) & ~sk
    rank = np.array([x[3] for x in rows])
    none = ~sk & ~made
    out = {"windows": len(rows), "skipped": float(sk.mean()), "made": float(made.mean()),
           "neither": float(none.mean())}  # fmt: skip
    for name, mask in (("skipped", sk), ("made", made), ("neither", none)):
        out[f"ratio_{name}"] = [float(np.quantile(r[mask], q)) for q in (0.1, 0.5, 0.9)]
    out["auc_vs_made"] = auc(-r[sk], -r[made])
    out["auc_vs_neither"] = auc(-r[sk], -r[none])
    out["auc_vs_all"] = auc(-r[sk], -r[~sk])
    near = rank == 0
    out["nearest"] = {"windows": int(near.sum()), "skipped": float(sk[near].mean()),
                      "auc_vs_all": auc(-r[near & sk], -r[near & ~sk])}  # fmt: skip
    slow = r < 0.6
    out["slow_below_0.6"] = {"share": float(slow.mean()), "skipped": float(sk[slow].mean()),
                             "neither": float(none[slow].mean())}  # fmt: skip
    return out


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m runningbattery.validate.teams",
                                     description=__doc__)  # fmt: skip
    parser.add_argument("folder", type=Path, help="a batch of natural matches with signals.json")
    parser.add_argument("--json", type=Path)
    args = parser.parse_args(argv)
    folders = sorted(p for p in args.folder.iterdir() if (p / SIGNALS).exists())
    teams = [team_measures(f) for f in folders]
    report: dict = {"matches": len(folders), "teams": {}}
    print(f"{len(folders)} matches: does the estimator pick the more tired team?")
    for tk, label in TRUTH.items():
        truth = np.array([x["home"][tk] - x["away"][tk] for x in teams])
        report["teams"][tk] = {}
        print(f"  truth: {label}")
        for sk in SEEN:
            seen = np.array([x["home"][sk] - x["away"][sk] for x in teams])
            a = agreement(seen, truth)
            report["teams"][tk][sk] = a
            print(
                f"    {sk:<13} same team {a['same_team']:.0%} (clear half "
                f"{a['same_team_clear_half']:.0%}), rho {a['rho']:+.2f}"
            )
    rows = [w for f in folders for w in chase_windows(f)]
    c = chase_summary(rows)
    report["chase"] = c
    print(
        f"{c['windows']} player-windows after turnovers: skipped {c['skipped']:.1%}, made "
        f"{c['made']:.1%}, neither {c['neither']:.1%}"
    )
    print(
        f"  AUC of low speed for a skipped run: vs made {c['auc_vs_made']:.2f}, vs neither "
        f"{c['auc_vs_neither']:.2f}, vs all {c['auc_vs_all']:.2f}; nearest player "
        f"{c['nearest']['auc_vs_all']:.2f}"
    )
    print(
        f"  below 60% of top speed: {c['slow_below_0.6']['share']:.0%} of windows, of which "
        f"skipped {c['slow_below_0.6']['skipped']:.1%}, no run asked "
        f"{c['slow_below_0.6']['neither']:.1%}"
    )
    if args.json:
        args.json.write_text(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
