"""Moment realism check: do the moments the feed shows happen in real matches, as often and
with the same facts?

``python -m runningbattery.validate.moments real=data/real/idsse synthetic=data/synthetic/realcheck
demo=data/synthetic/demo --json out.json``

Each ``name=folder`` is a group of match folders with ``signals.json`` (the estimator run). Real
matches are the IDSSE ones written by ``validate.real_events`` (their events converted from the
DFL feed, possession and transitions from the tracking). Every match goes through the same code
the feed uses: ``MatchTools.find_moments`` for each kind (all moments, not only the top ten),
the offline feed's picks (``feed.candidates``, ``pick_offline`` and ``ensure_key``: what would
reach the feed without the Tactical agent) and the highlight candidates and ranked highlights
(``agents.highlights``).

Rates are per 90 player-minutes (outfield players, time on the pitch) for player moments and
per match for team moments. Facts are the moments' own numbers (``facts[...]["value"]``), plus,
for a quiet spell (``not_tired_tactical``), the player's mean speed over its 5 minutes. No truth
is read: real matches have none.
"""

from __future__ import annotations

import argparse
import json
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

from runningbattery.agents import feed, highlights
from runningbattery.agents.tools import MOMENT_KINDS, MatchTools

FIVE_MIN_S = 300


def _flat(facts: dict) -> dict:
    out = {}
    for k, v in facts.items():
        if isinstance(v, dict) and "value" in v:
            out[k] = v["value"]
        elif isinstance(v, bool | int | float | str):
            out[k] = v
    return out


def collect(folder: Path) -> dict:
    """Every moment and highlight of one match, with what the feed would pick."""
    tools = MatchTools(folder)
    m = tools.m
    outfield_s = sum(len(s.t) for pid, s in m.series.items() if m.players[pid]["position"] != "GK")
    found = feed.candidates(tools, 8)
    picked = set(feed.ensure_key(feed.pick_offline(found), found))
    moments = []
    for kind in MOMENT_KINDS:
        for mo in tools.find_moments(kind, limit=10**6)["moments"]:
            row = {"kind": kind, "id": mo["id"], "video_s": mo["video_s"],
                   "score": mo["score"], "rank": mo["rank"], "feed": mo["id"] in picked,
                   **_flat(mo["facts"])}  # fmt: skip
            if mo.get("player"):
                row |= {"player": mo["player"]["id"], "position": mo["player"]["position"]}
            if kind == "not_tired_tactical":
                s = m.series[mo["player"]["id"]]
                i = s.index(mo["period"], mo["t"])
                row["mean_speed_5min"] = float(s.cols["speed"][max(i - FIVE_MIN_S + 1, 0) : i + 1]
                                               .mean())  # fmt: skip
            moments.append(row)
    cands = highlights.candidates(m)
    shown = {(e["kind"], e["player"], e["t"]) for e in highlights.ranked(cands)}
    hl = [
        {"kind": e["kind"], "player": e["player"], "position": m.players[e["player"]]["position"],
         "value": e["value"], "shown": (e["kind"], e["player"], e["t"]) in shown,
         **_flat(e["facts"])}
        for e in cands
    ]  # fmt: skip
    hsr = sum(float(m.hsr_per_s(pid).sum()) for pid in m.series
              if m.players[pid]["position"] != "GK")  # fmt: skip
    transitions = len({e.possession_id for e in m.events if e.phase is not None
                       and e.phase.value == "positive_transition"})  # fmt: skip
    return {
        "match": folder.name, "outfield_s": outfield_s, "hsr_m": hsr,
        "subs": len(m.metadata.substitutions), "transitions": transitions,
        "moments": moments, "highlights": hl,
    }  # fmt: skip


def folders(root: Path) -> list[Path]:
    return sorted(p.parent for p in root.glob("*/signals.json"))


def gather(groups: dict[str, Path], workers: int = 8) -> dict[str, list[dict]]:
    out = {}
    with ProcessPoolExecutor(workers) as pool:
        for name, root in groups.items():
            out[name] = list(pool.map(collect, folders(root)))
    return out


# --- Summary -------------------------------------------------------------------------------------

# (kind, fact, how to read it): the facts each moment's lines are built on.
FACTS = {
    "red_zone": ["hardest_minutes_count", "duration", "peak_1min_hsr", "typical_pro_battery_low"],
    "exposed_on_turnover": ["times_exposed_so_far", "hardest_minutes_so_far",
                            "distance_to_ball_at_turnover", "mean_speed_next_8s",
                            "typical_pro_battery"],
    "second_wind": ["vs_match_average", "minutes_after_hardest_minutes",
                    "match_average_per_min"],
    "fresh_legs": ["vs_teammates", "sub_hsr_per_min"],
    "not_tired_tactical": ["vs_match_average", "last_5min_hsr_per_min", "mean_speed_5min",
                           "match_average_per_min"],
    "tug_of_war": ["vs_opponent"],
    "flat_out": ["peak_speed", "share_of_top_speed"],
}  # fmt: skip
HL_FACTS = {
    "back_to_back": ["runs", "seconds", "longest_gap", "metres"],
    "busiest_minute": ["metres_in_one_minute"],
    "top_speed": ["top_speed"],
    "longest_run": ["metres"],
    "recovery_run": ["metres"],
}


def _q(xs: list[float]) -> str:
    xs = [x for x in xs if x is not None and x == x]
    if not xs:
        return "—"
    a = np.asarray(xs, dtype=float)
    p10, p50, p90 = np.percentile(a, [10, 50, 90])
    return f"{p50:.3g} [{p10:.3g}–{p90:.3g}] max {a.max():.3g} (n={len(a)})"


def summary(data: dict[str, list[dict]]) -> list[str]:
    lines = []
    for name, ms in data.items():
        p90 = sum(x["outfield_s"] for x in ms) / 5400.0
        lines.append(f"== {name}: {len(ms)} matches, {p90:.0f} outfield player-90s, "
                     f"{np.mean([x['transitions'] for x in ms]):.1f} transitions/match, "
                     f"HSR {sum(x['hsr_m'] for x in ms) / p90:.0f} m per player-90")  # fmt: skip
        for kind in MOMENT_KINDS:
            rows = [r for x in ms for r in x["moments"] if r["kind"] == kind]
            fed = [r for r in rows if r["feed"]]
            rate = len(rows) / (len(ms) if kind == "tug_of_war" else p90)
            unit = "per match" if kind == "tug_of_war" else "per player-90"
            lines.append(f"  {kind}: {rate:.2f} {unit}; in the feed {len(fed) / len(ms):.1f} "
                         f"per match; score (feed) {_q([r['score'] for r in fed])}")  # fmt: skip
            for fact in FACTS[kind]:
                lines.append(f"    {fact}: all {_q([r.get(fact) for r in rows])}; "
                             f"feed {_q([r.get(fact) for r in fed])}")  # fmt: skip
        for kind, facts in HL_FACTS.items():
            rows = [h for x in ms for h in x["highlights"] if h["kind"] == kind]
            shown = [h for h in rows if h["shown"]]
            lines.append(f"  highlight {kind}: {len(rows) / p90:.2f} per player-90, shown "
                         f"{len(shown) / len(ms):.1f} per match")  # fmt: skip
            for fact in facts:
                lines.append(f"    {fact}: all {_q([h.get(fact) for h in rows])}; "
                             f"shown {_q([h.get(fact) for h in shown])}")  # fmt: skip
    return lines


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m runningbattery.validate.moments",
                                     description=__doc__)  # fmt: skip
    parser.add_argument("groups", nargs="+", help="name=folder of match folders")
    parser.add_argument("--json", type=Path, help="write every moment and highlight here")
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args(argv)
    groups = {g.split("=", 1)[0]: Path(g.split("=", 1)[1]) for g in args.groups}
    data = gather(groups, args.workers)
    if args.json:
        args.json.write_text(json.dumps(data, default=float))
    print("\n".join(summary(data)))


if __name__ == "__main__":
    main()
