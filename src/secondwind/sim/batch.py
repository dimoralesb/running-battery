"""Statistics over many seeds: ``python -m secondwind.sim.batch --seeds 1-10``.

Simulates the matches in parallel, in memory (no files), and prints the mean ± SD across matches
of the match figures against the interim targets (``summary.TARGETS``), movement per position
against synthesis §4.2, running by phase, and the purpose of the high-intensity runs. Movement
comes from the noise-free positions. Every change to the generator shifts the random draws, so
tune on means over about 10 seeds, not on one match.
"""

from __future__ import annotations

import argparse
import os
from collections import Counter
from concurrent.futures import ProcessPoolExecutor

import numpy as np

from secondwind.schema import Position, RunPurpose
from secondwind.sim import params as P
from secondwind.sim.output import simulate
from secondwind.sim.runs import speeds, spells
from secondwind.sim.summary import TARGETS, event_counts, movement, transition_seconds

# Per-match targets by position, 2024/25: total, >5.5 m/s and >7 m/s distance (m)
# [synthesis §4.2: Allen2024, Table 4, scaled to Allen2025, Figs 2–3; derived].
POSITION_TARGETS = {
    "GK": (4720, 33, 2),
    "CB": (9830, 610, 140),
    "FB": (10710, 1070, 290),
    "DM": (11670, 840, 140),
    "CM": (11810, 930, 170),
    "AM": (11240, 1120, 270),
    "WM": (10870, 1190, 340),
    "CF": (10600, 1020, 280),
}
# Sprints above 6.94 m/s (25 km/h) lasting ≥ 0.7 s, per 98 min [Castellano2025, Table 3]. Their
# CM row is used for CM only, W for WM and FW for CF.
SPRINT_COUNT = dict(speed=6.94, min_s=0.7, minutes=98.0)
SPRINT_COUNT_TARGETS = {"CB": 7.2, "FB": 12.7, "CM": 8.8, "WM": 14.0, "CF": 13.2}
# Metres per minute per player slot by phase [Allen2026b, Table 5; dead ball derived].
PHASE_TARGETS = {"in_possession": 133.0, "out_of_possession": 145.0, "dead": 63.0}
MATCH_KEYS = ["passes", "shots", "duels", "fouls", "throw_ins", "corners", "offsides"]
MATCH_KEYS += ["transitions", "goals", "goal_kicks", "free_kicks", "crosses"]


def match_stats(seed: int) -> dict:
    """Everything the report needs from one match, as plain numbers."""
    m = simulate(seed, f"batch{seed:04d}")
    ids = [p.id for team in m.metadata.teams for p in team.players]
    positions = [p.position.value for team in m.metadata.teams for p in team.players]
    alive = np.concatenate([pf.alive for pf in m.periods])
    holder = np.concatenate([pf.possession for pf in m.periods])
    minutes = len(alive) / P.FRAME_RATE_HZ / 60.0
    moved = movement([pf.pos for pf in m.periods], ids)

    min_frames = round(SPRINT_COUNT["min_s"] * P.FRAME_RATE_HZ)
    sprints = np.zeros(22)
    phase_m = {name: np.zeros(22) for name in PHASE_TARGETS}
    phase_frames = {name: np.zeros(22) for name in PHASE_TARGETS}
    team_of = np.repeat([0, 1], 11)
    for pf in m.periods:
        speed = speeds(pf.pos)
        for j in range(22):
            sprints[j] += len(spells(speed[:, j] > SPRINT_COUNT["speed"], min_frames))
        step = speed / P.FRAME_RATE_HZ
        alive_k, holder_k = pf.alive[:-1, None], pf.possession[:-1, None]
        masks = {
            "in_possession": alive_k & (holder_k == team_of[None]),
            "out_of_possession": alive_k & (holder_k == 1 - team_of[None]),
            "dead": ~alive_k & np.ones((1, 22), dtype=bool),
        }
        for name, mask in masks.items():
            phase_m[name] += np.where(mask, step, 0.0).sum(axis=0)
            phase_frames[name] += mask.sum(axis=0)
    phase_rate = {
        name: float(phase_m[name].sum() / (phase_frames[name].sum() / P.FRAME_RATE_HZ / 60.0))
        for name in PHASE_TARGETS
    }
    held = alive & (holder >= 0)
    dead_starts = {
        pf.period: (np.flatnonzero(pf.alive[:-1] & ~pf.alive[1:]) + 1) / P.FRAME_RATE_HZ
        for pf in m.periods
    }
    return {
        "minutes": minutes,
        "ball_in_play_pct": 100.0 * float(alive.mean()),
        "home_possession_pct": 100.0 * float(np.mean(holder[held] == 0)),
        "counts": event_counts(m.events),
        "transition_s": transition_seconds(m.events, dead_starts),
        "positions": positions,
        "distance": [moved["distance_m"][i] for i in ids],
        "hid": [moved["hid_m"][i] for i in ids],
        "sprint": [moved["sprint_m"][i] for i in ids],
        "top_speed": [moved["top_speed"][i] for i in ids],
        "sprints_per_98": (sprints * SPRINT_COUNT["minutes"] / minutes).tolist(),
        "phase": phase_rate,
        "purposes": Counter(r.purpose.value for r in m.truth.runs),
        "runs": len(m.truth.runs),
    }


def parse_seeds(text: str) -> list[int]:
    """``1-10`` or ``1,4,7`` or a mix."""
    seeds: list[int] = []
    for part in text.split(","):
        lo, _, hi = part.partition("-")
        seeds += list(range(int(lo), int(hi or lo) + 1))
    return seeds


def run_batch(seeds: list[int], jobs: int | None = None) -> list[dict]:
    jobs = jobs or min(len(seeds), os.cpu_count() or 1)
    with ProcessPoolExecutor(max_workers=jobs) as pool:
        return list(pool.map(match_stats, seeds))


def mean_sd(values) -> str:
    v = np.asarray(values, dtype=float)
    return f"{v.mean():8.1f} ± {v.std(ddof=1) if len(v) > 1 else 0.0:6.1f}"


def report(stats: list[dict]) -> str:
    n = len(stats)
    lines = [f"{n} matches. Mean ± SD across matches."]
    lines.append("")
    lines.append(f"  {'match figure':<20}{'mean ± SD':>17}{'target':>9}")
    rows = [
        ("match_minutes", [s["minutes"] for s in stats]),
        ("ball_in_play_pct", [s["ball_in_play_pct"] for s in stats]),
        ("home_possession_pct", [s["home_possession_pct"] for s in stats]),
        ("transition_s", [s["transition_s"] for s in stats]),
    ]
    rows += [(key, [s["counts"][key] for s in stats]) for key in MATCH_KEYS]
    for key, values in rows:
        target = TARGETS.get(key, ("", ""))[0]
        lines.append(f"  {key:<20}{mean_sd(values):>17}{target:>9}")

    lines.append("")
    lines.append("  Movement by position (noise-free positions), per player per match.")
    lines.append(
        f"  {'pos':<4}{'n':>4}{'distance m':>18}{'target':>7}{'>5.5 m/s':>17}{'target':>7}"
        f"{'>7 m/s':>16}{'target':>7}{'sprints/98':>13}{'target':>7}{'top m/s mean (max)':>21}"
    )
    for pos in Position:
        key = pos.value
        names = ("distance", "hid", "sprint", "sprints_per_98", "top_speed")
        pick = [
            tuple(s[name][j] for name in names)
            for s in stats
            for j, p in enumerate(s["positions"])
            if p == key
        ]
        if not pick:
            continue
        dist, hid, sprint, count, top = (np.array(col) for col in zip(*pick, strict=True))
        td_t, hid_t, spr_t = POSITION_TARGETS[key]
        count_t = SPRINT_COUNT_TARGETS.get(key, "–")
        lines.append(
            f"  {key:<4}{len(dist):>4}{mean_sd(dist):>18}{td_t:>7}{mean_sd(hid):>17}{hid_t:>7}"
            f"{mean_sd(sprint):>16}{spr_t:>7}{mean_sd(count):>13}{count_t:>7}"
            f"{top.mean():>13.2f} ({top.max():.2f})"
        )

    lines.append("")
    lines.append("  Running by phase, m/min per player slot (GK included).")
    for name, target in PHASE_TARGETS.items():
        lines.append(f"  {name:<20}{mean_sd([s['phase'][name] for s in stats]):>17}{target:>9}")

    lines.append("")
    total = Counter()
    for s in stats:
        total.update(s["purposes"])
    runs = sum(s["runs"] for s in stats)
    lines.append(
        f"  High-intensity runs (>{P.HI_SPEED} m/s for ≥{P.HI_MIN_S} s): "
        f"{runs / n:.0f} per match, {runs / n / 22:.1f} per player."
    )
    for purpose in RunPurpose:
        k = total[purpose.value]
        lines.append(
            f"  {purpose.value:<20}{k / n:>8.1f} per match {100 * k / max(runs, 1):>6.1f}%"
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m secondwind.sim.batch", description=__doc__)
    parser.add_argument("--seeds", default="1-10", help="e.g. 1-10 or 1,3,5 (default 1-10)")
    parser.add_argument("--jobs", type=int, help="worker processes (default: one per seed)")
    args = parser.parse_args(argv)
    print(report(run_batch(parse_seeds(args.seeds), args.jobs)))


if __name__ == "__main__":
    main()
