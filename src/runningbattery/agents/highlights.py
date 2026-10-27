"""Physical highlights: the match's fastest, longest and busiest running,
measured from positions and told in football's words, with fixed captions the Verifier checks.

``python -m runningbattery.agents.highlights <match folder>`` prints them; ``runningbattery.export``
writes ``highlights.json`` for the overlay.

Six kinds, each ranked one entry per player:
- **top_speed**: the fastest second of a run, against the published match top speed for his
  position [SilvaH2025, Table 1].
- **longest_run**: one continuous run above 5.5 m/s (19.8 km/h), in metres, and where it went,
  against a typical high-speed run of about 19 m [Fang2024, Table 2; DiSalvo2007, p.224].
- **back_to_back**: three or more high-speed runs with at most ``BACK_TO_BACK_GAP_S`` between
  them (our assumption), against the usual gap for his position, 51–101 s [Bradley2009, Table I].
- **busiest_minute**: high-speed metres in one minute, against the published mean best minute,
  62 m [Leifsson2024, Table 1].
- **most_ground**: total distance at the final whistle (whole-match players), against the
  Premier League average for his position group [Kavanagh2024, Table 2; by position in
  Bradley2009, Table I].
- **recovery_run**: the longest high-speed run back towards his own goal that starts within
  ``RECOVERY_WITHIN_S`` of his team losing the ball (our assumption); speed and distance only.

Kept: each event that entered the top ``TOP`` players of its kind when it happened, so the top
``TOP`` so far at any moment are among them (the overlay picks them live). Measured facts only:
speed shows what a player did, never whether he tried (claim 38). Reads what the agents read
(``tools.MatchData``), never the truth file.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from runningbattery.agents import verifier
from runningbattery.agents.tools import MATCH_PEAK, MAX_PLAUSIBLE_SPEED, MatchData, q, runs
from runningbattery.engine import params as EP

TOP = 3
MIN_RUN_S = 1  # a high-speed run: at least 1 s above 5.5 m/s (the dwell of Allen2024, p.781)
BACK_TO_BACK_GAP_S = 20.0  # our assumption: under a third of the shortest usual gap (51 s)
BACK_TO_BACK_MIN = 3
BUSY_MIN_M = 40.0  # a minute counts from 40 m of high-speed running (our assumption)
TYPICAL_RUN_M = 19  # [Fang2024, Table 2: 19.2 m; DiSalvo2007, p.224: 19.3 m]
BEST_MINUTE_M = 62  # [Leifsson2024, Table 1]
RECOVERY_WITHIN_S = 10  # a recovery run starts within 10 s of the loss (our assumption)
# Premier League total distance per match by position group [Kavanagh2024, Table 2: defenders
# 9,966, midfielders 11,594, forwards 10,710 m]; Bradley2009, Table I by position agrees within
# 1–8% (CB 9,885, FB 10,710, CM 11,450, WM 11,535, A 10,314 m).
GROUP_DISTANCE_M = {"defender": 9966, "midfielder": 11594, "forward": 10710}
GROUP = {"CB": "defender", "FB": "defender", "DM": "midfielder", "CM": "midfielder",
         "AM": "midfielder", "WM": "midfielder", "CF": "forward"}  # fmt: skip
# Usual time between high-speed (> 5.5 m/s) runs by position, Premier League [Bradley2009,
# Table I]; DM and AM take the central midfielders' value.
USUAL_GAP_S = {"CB": 101, "FB": 74, "DM": 62, "CM": 62, "AM": 62, "WM": 51, "CF": 73}
POSITION_NAME = {"CB": "centre-back", "FB": "full-back", "DM": "defensive midfielder",
                 "CM": "central midfielder", "AM": "attacking midfielder", "WM": "wide midfielder",
                 "CF": "striker"}  # fmt: skip
KINDS = {
    "top_speed": "Top speed",
    "longest_run": "Longest run",
    "back_to_back": "Back-to-back runs",
    "busiest_minute": "Busiest minute",
    "most_ground": "Most ground covered",
    "recovery_run": "Recovery run",
}
SRC = "signals.players[].series.speed (1-s mean)"
SOURCES = {
    "top_speed": ["SilvaH2025"],
    "longest_run": ["Fang2024", "DiSalvo2007"],
    "back_to_back": ["Bradley2009"],
    "busiest_minute": ["Leifsson2024"],
    "most_ground": ["Kavanagh2024", "Bradley2009"],
    "recovery_run": ["Fang2024", "DiSalvo2007"],
}


def zone(m: MatchData, pid: str, period: int, k: int) -> tuple[str, float] | None:
    """Where a player is at second k, in his team's direction of attack, and his x towards the
    opponents' goal (m)."""
    xy = m.xy[period][k, m.col[pid]]
    if np.isnan(xy[0]):
        return None
    forward = m.teams[m.players[pid]["team"]].attacks_positive_x_in_period_1 == (period == 1)
    x = float(xy[0]) * (1 if forward else -1)
    in_box = abs(float(xy[1])) <= 20.16
    if x <= -36.0 and in_box:
        return "his own box", x
    if x < 0:
        return "his own half", x
    if x >= 36.0 and in_box:
        return "the opponents' box", x
    return "the opponents' half", x


def where(m: MatchData, pid: str, period: int, k0: int, k1: int) -> str | None:
    """'from his own half into the opponents' box', 'back towards his own goal', …"""
    a, b = zone(m, pid, period, k0), zone(m, pid, period, k1)
    if not a or not b:
        return None
    if b[1] - a[1] <= -10.0:
        return "back towards his own goal"
    if a[0] == b[0]:
        return f"in {a[0]}"
    return f"from {a[0]} into {b[0]}"


def _player_runs(m: MatchData, pid: str) -> list[dict]:
    """His high-speed runs: per period, each stretch of seconds above 5.5 m/s."""
    s = m.series[pid]
    v = np.where(s.cols["speed"] <= MAX_PLAUSIBLE_SPEED, s.cols["speed"], 0.0)
    out = []
    for per in (1, 2):
        rows = np.flatnonzero(s.period == per)
        for a, b in runs(v[rows] > EP.HI_SPEED):
            i0, i1 = int(rows[a]), int(rows[b])
            if i1 - i0 + 1 < MIN_RUN_S:
                continue
            seg = v[i0 : i1 + 1]
            out.append({"period": per, "i0": i0, "i1": i1, "t0": float(s.t[i0]),
                        "t1": float(s.t[i1]), "metres": float(seg.sum()),
                        "top": float(seg.max()), "i_top": i0 + int(np.argmax(seg))})  # fmt: skip
    return out


def losses(m: MatchData, team: str) -> dict[int, np.ndarray]:
    """Per period, the seconds at which ``team`` lost the ball: the opponents have it and the
    last team seen with it (dead-ball seconds skipped) was ``team``."""
    out = {}
    for per, poss in m.possession.items():
        last, ks = None, []
        for k, holder in enumerate(poss):
            if holder and holder != team and last == team:
                ks.append(k)
            last = holder or last
        out[per] = np.array(ks, dtype=int)
    return out


def _whole_match(m: MatchData, pid: str) -> bool:
    s = m.series[pid]
    return bool(m.players[pid]["starter"] and pid not in m.sub_off and s.period[-1] == 2
                and s.t[-1] >= m.durations[2] - 5.0)  # fmt: skip


def candidates(m: MatchData) -> list[dict]:
    """Every event of every kind, unranked."""
    out = []
    lost = {team: losses(m, team) for team in m.teams}
    ground = []
    for pid, s in m.series.items():
        info = m.players[pid]
        if info["position"] == "GK":
            continue
        if _whole_match(m, pid):
            v = np.where(s.cols["speed"] <= MAX_PLAUSIBLE_SPEED, s.cols["speed"], 0.0)
            metres = float(v.sum())  # 1-s mean speeds, so metres
            group = GROUP[info["position"]]
            ground.append({
                "kind": "most_ground", "player": pid, "period": 2, "t0": 0.0,
                "t1": float(s.t[-1]), "t": float(s.t[-1]), "value": metres,
                "segments": [],
                "facts": {
                    "km": q(metres / 1000.0, "km", SRC, 1),
                    "metres": q(metres, "m", SRC, 0),
                    "published_for_position": q(GROUP_DISTANCE_M[group] / 1000.0,
                                                f"km, Premier League {group}s' average",
                                                "Kavanagh2024, Table 2", 1),
                    "group": f"{group}s",
                },
            })  # fmt: skip
        rs = _player_runs(m, pid)
        for r in rs:
            per = r["period"]
            k0, k1 = m.second(per, r["t0"]), m.second(per, r["t1"])
            ev = {"player": pid, "period": per, "t0": r["t0"], "t1": r["t1"]}
            top = r["top"]
            out.append(ev | {"kind": "top_speed", "t": float(s.t[r["i_top"]]), "value": top,
                             "facts": {
                                 "top_speed": q(top, "m/s", SRC, 1),
                                 "top_speed_kmh": q(top * 3.6, "km/h", SRC, 0),
                                 "published_match_top_speed_for_position": q(
                                     MATCH_PEAK[info["position"]], "m/s, mean match top speed "
                                     "for his position", "SilvaH2025, Table 1", 1),
                             }})  # fmt: skip
            run = {
                "metres": q(r["metres"], "m above 5.5 m/s in one run", SRC, 0),
                "seconds": q(r["t1"] - r["t0"] + 1.0, "s", SRC, 0),
                "top_speed": q(top, "m/s", SRC, 1),
                "typical_run": q(TYPICAL_RUN_M, "m, mean high-speed run",
                                 "Fang2024, Table 2; DiSalvo2007, p.224", 0),
                "times_typical": q(r["metres"] / TYPICAL_RUN_M, "times a typical run", SRC, 0),
            }  # fmt: skip
            went = where(m, pid, per, k0, k1)
            if went:
                run["where"] = went
            holder = m.possession[per][k0]
            if holder:
                run["ball"] = "his team" if holder == info["team"] else "the opponents"
            out.append(ev | {"kind": "longest_run", "t": r["t1"], "value": r["metres"],
                             "facts": run})  # fmt: skip
            # A recovery run: back towards his own goal, starting just after his team lost it.
            ks = lost[info["team"]][per]
            before = ks[(ks <= k0) & (ks >= k0 - RECOVERY_WITHIN_S)]
            if went == "back towards his own goal" and before.size:
                a, b = zone(m, pid, per, k0), zone(m, pid, per, k1)
                rec = {k: run[k] for k in ("metres", "seconds", "top_speed", "typical_run")}
                rec |= {
                    "top_speed_kmh": q(top * 3.6, "km/h", SRC, 0),
                    "seconds_after_loss": q(k0 - int(before[-1]), "s after his team lost the "
                                            "ball", "tracking.possession_team", 0),
                    "metres_back": q(a[1] - b[1], "m back towards his own goal",
                                     "tracking positions", 0),
                }  # fmt: skip
                out.append(ev | {"kind": "recovery_run", "t": r["t1"], "value": r["metres"],
                                 "facts": rec})  # fmt: skip
        # Back-to-back: runs whose gaps (end of one to start of the next) are all short.
        bout: list[dict] = []
        for r in [*rs, None]:
            if (
                r
                and bout
                and r["period"] == bout[-1]["period"]
                and (r["t0"] - bout[-1]["t1"] - 1.0 <= BACK_TO_BACK_GAP_S)
            ):
                bout.append(r)
                continue
            if len(bout) >= BACK_TO_BACK_MIN:
                gaps = [b["t0"] - a["t1"] - 1.0 for a, b in zip(bout, bout[1:], strict=False)]
                usual = USUAL_GAP_S[info["position"]]
                out.append({
                    "kind": "back_to_back", "player": pid, "period": bout[0]["period"],
                    "t0": bout[0]["t0"], "t1": bout[-1]["t1"], "t": bout[-1]["t1"],
                    "value": len(bout) + sum(b["metres"] for b in bout) / 1e4,  # count, then m
                    "segments": [[b["t0"], b["t1"]] for b in bout],
                    "facts": {
                        "runs": q(len(bout), "high-speed runs", SRC),
                        "seconds": q(bout[-1]["t1"] - bout[0]["t0"] + 1.0, "s", SRC, 0),
                        "metres": q(sum(b["metres"] for b in bout), "m above 5.5 m/s", SRC, 0),
                        "longest_gap": q(max(gaps), "s between runs", SRC, 0),
                        "usual_gap_for_position": q(usual, "s, usual time between high-speed "
                                                    "runs for his position",
                                                    "Bradley2009, Table I", 0),
                    },
                })  # fmt: skip
            bout = [r] if r else []
        # Busiest minute: the peak of each stretch of minutes with >= BUSY_MIN_M m.
        h = s.cols["hsr_1min"]
        for per in (1, 2):
            rows = np.flatnonzero(s.period == per)
            for a, b in runs(h[rows] >= BUSY_MIN_M):
                i = int(rows[a] + np.argmax(h[rows[a] : rows[b] + 1]))
                t = float(s.t[i])
                out.append({
                    "kind": "busiest_minute", "player": pid, "period": per,
                    "t0": max(t - 59.0, 0.0), "t1": t, "t": t, "value": float(h[i]),
                    "facts": {
                        "metres_in_one_minute": q(float(h[i]), "m above 5.5 m/s in one minute",
                                                  "signals.players[].series.hsr_1min", 0),
                        "published_best_minute": q(BEST_MINUTE_M, "m, mean best minute",
                                                   "Leifsson2024, Table 1", 0),
                    },
                })  # fmt: skip
    # All at the final whistle: only the top TOP.
    return out + sorted(ground, key=lambda e: -e["value"])[:TOP]


def ranked(events: list[dict]) -> list[dict]:
    """Per kind, in match order: keep an event when it is its player's new best and that best
    is among the top TOP players so far."""
    keep = []
    order = sorted(events, key=lambda e: (e["period"], e["t"]))
    for kind in KINDS:
        best: dict[str, float] = {}
        for e in order:
            if e["kind"] != kind or e["value"] <= best.get(e["player"], -1.0):
                continue
            best[e["player"]] = e["value"]
            if sorted(best.values(), reverse=True).index(e["value"]) < TOP:
                keep.append(e)
    return keep


def caption(m: MatchData, e: dict) -> str:
    """The sentence the overlay shows (football's words; measured facts only)."""
    p = m.players[e["player"]]
    name, f = p["name"], e["facts"]

    def v(key):
        x = f[key]["value"]
        if f[key]["unit"].startswith("m/s"):
            return f"{x:.1f}"
        return int(x) if isinstance(x, float) and x.is_integer() else x

    pos = POSITION_NAME[p["position"]]
    a_pos = f"{'an' if pos[0] in 'aeiou' else 'a'} {pos}"
    if e["kind"] == "top_speed":
        return (
            f"{name} hits {v('top_speed')} m/s ({v('top_speed_kmh')} km/h); the average match "
            f"top speed for {a_pos} is about "
            f"{v('published_match_top_speed_for_position')} m/s."
        )
    if e["kind"] == "longest_run":
        went = f" {f['where']}" if f.get("where") else ""
        ball = {
            "his team": " with his team on the ball",
            "the opponents": " while the opponents had the ball",
        }.get(f.get("ball"), "")
        return (
            f"{name} runs {v('metres')} m above 5.5 m/s (19.8 km/h) in one go{went}{ball}, about "
            f"{v('times_typical')} times a typical high-speed run."
        )
    if e["kind"] == "back_to_back":
        return (
            f"{name} makes {v('runs')} high-speed runs in {v('seconds')} seconds, never more "
            f"than {v('longest_gap')} seconds apart; {a_pos} usually gets about "
            f"{v('usual_gap_for_position')} seconds between them."
        )
    if e["kind"] == "most_ground":
        return (
            f"{name} covered {v('km')} km over the match; Premier League {f['group']} average "
            f"about {v('published_for_position')} km."
        )
    if e["kind"] == "recovery_run":
        s = v("seconds_after_loss")
        return (
            f"{name} runs {v('metres')} m above 5.5 m/s back towards his own goal, up to "
            f"{v('top_speed')} m/s ({v('top_speed_kmh')} km/h), starting {s} "
            f"second{'' if s == 1 else 's'} after his team lost the ball."
        )
    return (
        f"{name} covers {v('metres_in_one_minute')} m above 5.5 m/s (19.8 km/h) in one "
        f"minute, against a published average best minute of {BEST_MINUTE_M} m."
    )


def highlights(m: MatchData) -> list[dict]:
    """The ranked events with times, captions and sources; each caption passes the rules."""
    out = []
    for e in ranked(candidates(m)):
        p = m.players[e["player"]]
        text = caption(m, e)
        v = verifier.verify(text, "fan", {"facts": e["facts"]})
        if not v.ok:
            raise ValueError(f"highlight caption fails the Verifier: {text} {v.findings}")
        when = m.when(e["period"], e["t"])
        out.append({
            "kind": e["kind"], "label": KINDS[e["kind"]], "value": round(e["value"], 2),
            "player": {k: p[k] for k in ("id", "name", "shirt", "team", "position")},
            **when,
            "start_video_s": m.video_s(e["period"], e["t0"]),
            "end_video_s": m.video_s(e["period"], e["t1"] + 1.0),
            "segments": [[m.video_s(e["period"], a), m.video_s(e["period"], b + 1.0)]
                         for a, b in e.get("segments", [[e["t0"], e["t1"]]])],
            "caption": text, "facts": e["facts"],
            "sources": SOURCES[e["kind"]] + sorted({x["source"] for x in e["facts"].values()
                                                    if isinstance(x, dict)}),
        })  # fmt: skip
    return sorted(out, key=lambda x: x["video_s"])


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m runningbattery.agents.highlights",
                                     description=__doc__)  # fmt: skip
    parser.add_argument("folder", type=Path)
    args = parser.parse_args(argv)
    hl = highlights(MatchData(args.folder))
    for kind in KINDS:
        rows = [h for h in hl if h["kind"] == kind]
        print(f"{KINDS[kind]}: {len(rows)} kept")
        for h in sorted(rows, key=lambda h: -h["value"])[:TOP]:
            print(f"  {h['clock']:>8}  {h['caption']}")
    print(json.dumps({"kept": len(hl)}))


if __name__ == "__main__":
    main()
