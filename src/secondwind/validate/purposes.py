"""Can a run's purpose be read from positions? Positions-only rules for "pressing" and
"recovery run" against the generator's hidden run purposes (PLAN decision 30).

``python -m secondwind.validate.purposes data/synthetic/dev [--json out.json] [--workers 8]``

The truth is ``truth.json`` ``runs``: each high-intensity run of the noise-free positions with
the purpose behind most of its frames, in Ju2022's classes. Ours are the runs an analyst can see:
seconds above 5.5 m/s (19.8 km/h) in the estimator's 1-s speed, as the highlights find them
(``agents.highlights``). A run of ours takes the purpose of the truth run it overlaps most
(``none`` if it overlaps none). Each rule labels runs from what real tracking has, possession
and positions:

- **press_ju** (close down / press: "runs directly towards opposition player on or receiving the
  ball" [Ju2022, Table 1]): his team without the ball when the run starts, the gap to the ball
  shrinking by at least ``PRESS_CLOSE_M`` over the run and at most ``PRESS_END_M`` at its end.
- **press_high**: press_ju with the ball in the opponents' third (``tools.THIRD_X``) at the
  start, what football calls pressing high.
- **recovery_ju** (recovery run: "runs back towards their own goal to be goal side when out of
  position" [Ju2022, Table 1]): his team without the ball at the start, at least ``BACK_M`` back
  towards his own goal, and starting on the wrong side of the ball (nearer the opponents' goal
  than the ball is).
- **recovery_highlight**: the overlay's recovery-run highlight (decision 29): at least 10 m back
  towards his own goal, starting within 10 s of his team losing the ball.

Reported per rule, by runs and by metres above 5.5 m/s: precision (share of the runs it labels
whose truth purpose is the target), recall (share of the target's runs it labels; truth runs our
1-s speed never sees count as missed) and the base rate (the target's share of all our runs).
Thresholds are our assumptions, set before the first run and not tuned on it. The rules can only
match a purpose the generator drew from the same positions, so a good score here is necessary,
not sufficient, for real matches.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

from secondwind.agents.highlights import RECOVERY_WITHIN_S, _player_runs, losses, where
from secondwind.agents.tools import THIRD_X, MatchData
from secondwind.io import SIGNALS, read_truth

PRESS_CLOSE_M = 3.0  # the gap to the ball shrinks by at least 3 m over the run
PRESS_END_M = 5.0  # and ends within 5 m of the ball (the presser is goal-side, about 1–2 m off)
BACK_M = 10.0  # back towards his own goal, as the highlights' "back towards his own goal"
OUT = ("after_losing", "off_ball_high", "off_ball_deep")  # tools.SITUATIONS without the ball
RULES = {
    "press_ju": ("close_down",),
    "press_high": ("close_down",),
    "recovery_ju": ("recovery_run",),
    "recovery_highlight": ("recovery_run",),
}


def _x_forward(m: MatchData, team: str, period: int, x: float) -> float:
    forward = m.teams[team].attacks_positive_x_in_period_1 == (period == 1)
    return float(x) * (1.0 if forward else -1.0)


def labelled_runs(folder: Path) -> tuple[list[dict], Counter]:
    """Our runs in one match, each with its truth purpose and the rules that label it; and
    the truth's executed runs per purpose (outfield players)."""
    m, tru = MatchData(folder), read_truth(folder)
    truth: dict[tuple[str, int], list] = {}
    totals: Counter = Counter()
    for r in tru.runs:
        if r.executed and m.players.get(r.player_id, {}).get("position") not in (None, "GK"):
            truth.setdefault((r.player_id, r.period), []).append(r)
            totals[r.purpose.value] += 1
    lost = {team: losses(m, team) for team in m.teams}
    out = []
    for pid, info in m.players.items():
        if info["position"] == "GK" or pid not in m.series:
            continue
        team, j = info["team"], m.col[pid]
        for run in _player_runs(m, pid):
            per, t0, t1 = run["period"], run["t0"], run["t1"]
            k0, k1 = m.second(per, t0), m.second(per, t1 + 1.0)
            # The truth run it overlaps most (truth times are 10 Hz; ours cover [t0, t1 + 1)).
            best, purpose = 0.0, "none"
            for r in truth.get((pid, per), []):
                ov = min(r.t_end, t1 + 1.0) - max(r.t_start, t0)
                if ov > best:
                    best, purpose = ov, r.purpose.value
            a, b = m.xy[per][k0, j], m.xy[per][k1, j]
            ball_a, ball_b = m.ball[per][k0], m.ball[per][k1]
            if np.isnan(a[0]) or np.isnan(b[0]):
                continue
            out_of_poss = m.situations[per][team][k0] in OUT
            gap0, gap1 = float(np.hypot(*(a - ball_a))), float(np.hypot(*(b - ball_b)))
            press = out_of_poss and gap0 - gap1 >= PRESS_CLOSE_M and gap1 <= PRESS_END_M
            xa, xb = _x_forward(m, team, per, a[0]), _x_forward(m, team, per, b[0])
            ball_x = _x_forward(m, team, per, ball_a[0])
            ks = lost[team][per]
            just_lost = bool(((ks <= k0) & (ks >= k0 - RECOVERY_WITHIN_S)).any())
            labels = {
                "press_ju": press,
                "press_high": press and ball_x >= THIRD_X,
                "recovery_ju": out_of_poss and xa - xb >= BACK_M and xa > ball_x,
                "recovery_highlight": just_lost
                and where(m, pid, per, k0, k1 - 1) == "back towards his own goal",
            }
            out.append({"purpose": purpose, "metres": run["metres"],
                        "labels": [k for k, v in labels.items() if v]})  # fmt: skip
    return out, totals


def score(runs: list[dict], totals: Counter) -> dict:
    """Precision, recall and base rate per rule, by runs and by metres."""
    n_all = len(runs)
    m_all = sum(r["metres"] for r in runs) or 1.0
    rep: dict = {"runs": n_all, "truth_runs": dict(totals)}
    for rule, targets in RULES.items():
        hit = [r for r in runs if rule in r["labels"]]
        good = [r for r in hit if r["purpose"] in targets]
        target = [r for r in runs if r["purpose"] in targets]
        found = [r for r in target if rule in r["labels"]]
        n_truth = sum(totals[t] for t in targets)
        metres = lambda rs: sum(r["metres"] for r in rs)  # noqa: E731
        rep[rule] = {
            "target": "/".join(targets),
            "labelled": len(hit),
            "precision": len(good) / len(hit) if hit else float("nan"),
            "recall": len(found) / n_truth if n_truth else float("nan"),
            "recall_of_seen": len(found) / len(target) if target else float("nan"),
            "base_rate": len(target) / n_all if n_all else float("nan"),
            "precision_m": metres(good) / metres(hit) if hit else float("nan"),
            "recall_m": metres(found) / metres(target) if target else float("nan"),
            "base_rate_m": metres(target) / m_all,
            "labelled_as": dict(Counter(r["purpose"] for r in hit).most_common(5)),
        }
    return rep


def _one(folder: str) -> tuple[list[dict], Counter]:
    return labelled_runs(Path(folder))


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m secondwind.validate.purposes",
                                     description=__doc__)  # fmt: skip
    parser.add_argument("folder", type=Path, help="a batch of matches with signals.json")
    parser.add_argument("--json", type=Path)
    parser.add_argument("--workers", type=int, default=1)
    args = parser.parse_args(argv)
    folders = sorted(str(p) for p in args.folder.iterdir() if (p / SIGNALS).exists())
    with ProcessPoolExecutor(args.workers) as pool:
        done = list(pool.map(_one, folders))
    runs = [r for rs, _ in done for r in rs]
    totals = sum((c for _, c in done), Counter())
    rep = score(runs, totals) | {"matches": len(folders)}
    print(f"{len(folders)} matches, {rep['runs']} high-speed runs of ours (outfield)")
    for rule in RULES:
        r = rep[rule]
        print(
            f"  {rule:<19} {r['labelled']:>6} labelled: precision {r['precision']:.2f} "
            f"(base rate {r['base_rate']:.2f}), recall {r['recall']:.2f} (of the runs we see "
            f"{r['recall_of_seen']:.2f}); by metres {r['precision_m']:.2f} / {r['recall_m']:.2f}"
            f"; labelled as {r['labelled_as']}"
        )
    if args.json:
        args.json.write_text(json.dumps(rep, indent=1))


if __name__ == "__main__":
    main()
