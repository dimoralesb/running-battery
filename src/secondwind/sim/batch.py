"""Statistics over many seeds: ``python -m secondwind.sim.batch --seeds 1-30``.

Simulates the matches in parallel, in memory (no files), and prints the mean ± SD across matches
of the match figures against the interim targets (``summary.TARGETS``), movement per position
and per team against synthesis §4.2, running and high-speed running by phase, the purpose of the
high-intensity runs, the time in each speed and acceleration band, and the spacing between
players (``sim.spacing``). ``--json`` also writes the report as JSON, so two runs can be
compared; ``--idsse`` adds the IDSSE bands (``sim.idsse``) and, once ``sim.spacing --idsse`` has
cached the IDSSE positions, the IDSSE spacing.

Two views of the movement:

- *Truth*: the noise-free positions. Distances, top speed, running by phase and run purposes.
- *Observed*: ``tracking.jsonl`` as the estimator sees it (noise and dropouts), smoothed as in
  ``summary.smooth``, then speed and tangential acceleration by central differences
  (``summary.kinematics``). Speed and acceleration bands and effort counts (sprints, high
  decelerations) come from here, because IDSSE and the papers measured them on smoothed
  tracking too.

Every change to the generator shifts the random draws, so tune on means over 30 seeds, not on
one match.
"""

from __future__ import annotations

import argparse
import json
import os
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

from secondwind.schema import Position, RunPurpose
from secondwind.sim import params as P
from secondwind.sim import spacing
from secondwind.sim.output import simulate
from secondwind.sim.runs import speeds
from secondwind.sim.summary import (
    ACCEL_EDGES,
    ACCEL_LABELS,
    EFFORT_MINUTES,
    SPEED_EDGES,
    SPEED_LABELS,
    TARGETS,
    band_seconds,
    effort_count,
    event_counts,
    kinematics,
    movement,
    smooth,
    transition_seconds,
)

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
POSITION_TOLERANCE = 0.05  # ±5% (synthesis §4.2; PLAN §2.5)
# Goalkeepers barely sprint: 2 ± 6 m above 7 m/s (25.2 km/h) [Allen2024, Table 4], so ±5% of the
# target means nothing. Their >7 m/s distance is judged within ±5 m of it instead (our choice).
GK_SPRINT_TOLERANCE_M = 5.0
# Team totals per match, mean (SD): total, >5.5 m/s, >7 m/s (m) [Allen2025, Figs 2–3].
TEAM_TARGETS = {"distance": (113891, 4097), "hid": (9611, 1300), "sprint": (2326, 471)}
# Efforts per 98 min [Castellano2025, Table 3]: sprints >6.94 m/s and decelerations < -3 m/s²,
# each ≥ 0.7 s (summary.EFFORTS). Their CD row is used for CB, CM for CM only, WN for WM and FW
# for CF. Broadcast tracking: compare counts loosely (±30%, PLAN §2.5); deceleration counts
# depend most on the system (synthesis §2.2), so they are shown, not tuned.
SPRINT_COUNT_TARGETS = {"CB": 7.2, "FB": 12.7, "CM": 8.8, "WM": 14.0, "CF": 13.2}
HIGH_DECEL_TARGETS = {"CB": 13.3, "FB": 20.7, "CM": 16.1, "WM": 21.9, "CF": 20.3}
# Mean match peak speed, m/s [SilvaH2025, Table 1]; their FW row is used for CF.
TOP_SPEED_TARGETS = {"CB": 8.09, "FB": 8.79, "CM": 8.41, "WM": 8.52, "CF": 8.29}
# Metres per minute per player slot by phase: total [Allen2026b, Table 5; dead ball derived]
# and >5.5 m/s (middle of the ranges 11.5–12.8 and 14.8–17.6) [Allen2026b, Table 5].
PHASE_TARGETS = {"in_possession": 133.0, "out_of_possession": 145.0, "dead": 63.0}
PHASE_HID_TARGETS = {"in_possession": 12.1, "out_of_possession": 16.2}
PHASE_TOLERANCE = 0.10  # PLAN §2.5
BAND_TOLERANCE = 3.0  # percentage points per speed band against IDSSE (PLAN §2.5)
# Share of high-intensity runs by purpose in peak periods, players [Ju2022, p.975]: recovery
# runs 28–34%, covering 22–25%, support play 11%.
PURPOSE_TARGETS = {"recovery_run": "28–34", "covering": "22–25", "support_play": "11"}
MATCH_KEYS = ["passes", "shots", "duels", "fouls", "throw_ins", "corners", "offsides"]
MATCH_KEYS += ["transitions", "goals", "goal_kicks", "free_kicks", "crosses"]
PER_PLAYER = ["distance", "hid", "sprint", "top_speed", "sprints_per_98", "hdec_per_98"]
PER_PLAYER += ["observed_distance"]


def observed_kinematics(m) -> tuple[list[np.ndarray], list[np.ndarray]]:
    """Speed and acceleration per period from the noisy tracking with dropouts, smoothed."""
    out_v, out_a = [], []
    for obs in m.observed:
        xy = np.where(obs.seen[..., None], obs.pos, np.nan)
        v, a = kinematics(smooth(xy))
        out_v.append(v)
        out_a.append(a)
    return out_v, out_a


def match_stats(seed: int) -> dict:
    """Everything the report needs from one match, as plain numbers."""
    m = simulate(seed, f"batch{seed:04d}")
    ids = [p.id for team in m.metadata.teams for p in team.players]
    positions = [p.position.value for team in m.metadata.teams for p in team.players]
    is_gk = np.array([p == "GK" for p in positions])
    alive = np.concatenate([pf.alive for pf in m.periods])
    holder = np.concatenate([pf.possession for pf in m.periods])
    minutes = len(alive) / P.FRAME_RATE_HZ / 60.0
    moved = movement([pf.pos for pf in m.periods], ids)

    phase_m = {name: np.zeros(22) for name in PHASE_TARGETS}
    phase_hid = {name: np.zeros(22) for name in PHASE_TARGETS}
    phase_frames = {name: np.zeros(22) for name in PHASE_TARGETS}
    team_of = np.repeat([0, 1], 11)
    for pf in m.periods:
        speed = speeds(pf.pos)
        step = speed / P.FRAME_RATE_HZ
        alive_k, holder_k = pf.alive[:-1, None], pf.possession[:-1, None]
        masks = {
            "in_possession": alive_k & (holder_k == team_of[None]),
            "out_of_possession": alive_k & (holder_k == 1 - team_of[None]),
            "dead": ~alive_k & np.ones((1, 22), dtype=bool),
        }
        for name, mask in masks.items():
            phase_m[name] += np.where(mask, step, 0.0).sum(axis=0)
            phase_hid[name] += np.where(mask & (speed > P.HI_SPEED), step, 0.0).sum(axis=0)
            phase_frames[name] += mask.sum(axis=0)

    def per_min(metres: dict[str, np.ndarray], name: str) -> float:
        return float(metres[name].sum() / (phase_frames[name].sum() / P.FRAME_RATE_HZ / 60.0))

    obs_v, obs_a = observed_kinematics(m)
    sprints, hdecs, obs_dist = np.zeros(22), np.zeros(22), np.zeros(22)
    speed_s = {g: np.zeros(len(SPEED_EDGES) - 1) for g in ("outfield", "GK")}
    accel_s = {g: np.zeros(len(ACCEL_EDGES) - 1) for g in ("outfield", "GK")}
    for v, a in zip(obs_v, obs_a, strict=True):
        obs_dist += np.nansum(v, axis=0) / P.FRAME_RATE_HZ
        for j in range(22):
            sprints[j] += effort_count(v[:, j], "sprint")
            hdecs[j] += effort_count(-a[:, j], "high_decel")
        for group, cols in (("outfield", ~is_gk), ("GK", is_gk)):
            speed_s[group] += band_seconds(v[:, cols], SPEED_EDGES)
            accel_s[group] += band_seconds(a[:, cols], ACCEL_EDGES)

    held = alive & (holder >= 0)
    dead_starts = {
        pf.period: (np.flatnonzero(pf.alive[:-1] & ~pf.alive[1:]) + 1) / P.FRAME_RATE_HZ
        for pf in m.periods
    }
    per_98 = EFFORT_MINUTES / minutes
    return {
        "seed": seed,
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
        "observed_distance": obs_dist.tolist(),
        "sprints_per_98": (sprints * per_98).tolist(),
        "hdec_per_98": (hdecs * per_98).tolist(),
        "phase": {name: per_min(phase_m, name) for name in PHASE_TARGETS},
        "phase_hid": {name: per_min(phase_hid, name) for name in PHASE_HID_TARGETS},
        "speed_s": {g: s.tolist() for g, s in speed_s.items()},
        "accel_s": {g: s.tolist() for g, s in accel_s.items()},
        "purposes": dict(Counter(r.purpose.value for r in m.truth.runs)),
        "runs": len(m.truth.runs),
        "spacing": spacing.sim_measure(m),
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


def describe(values, target=None) -> dict:
    """Mean and SD; with a target, how far off the mean is and its standard error, in %."""
    v = np.asarray(values, dtype=float)
    out = {"mean": float(v.mean()), "sd": float(v.std(ddof=1)) if len(v) > 1 else 0.0}
    if target is not None:
        out["target"] = target
        out["off_pct"] = 100.0 * (out["mean"] / target - 1.0)
        out["se_pct"] = 100.0 * out["sd"] / np.sqrt(len(v)) / target
    return out


def band_pct(stats: list[dict], key: str, group: str) -> list[float]:
    total = np.sum([s[key][group] for s in stats], axis=0)
    return (100.0 * total / total.sum()).tolist()


def build_report(stats: list[dict], idsse: list[dict] | None = None) -> dict:
    """All the batch numbers in one JSON-ready dict; ``format_report`` prints it."""
    rep: dict = {"n": len(stats), "seeds": [s["seed"] for s in stats]}
    rows = {
        "match_minutes": [s["minutes"] for s in stats],
        "ball_in_play_pct": [s["ball_in_play_pct"] for s in stats],
        "home_possession_pct": [s["home_possession_pct"] for s in stats],
        "transition_s": [s["transition_s"] for s in stats],
    }
    rows |= {key: [s["counts"][key] for s in stats] for key in MATCH_KEYS}
    rep["match"] = {k: describe(v, TARGETS.get(k, (None,))[0]) for k, v in rows.items()}

    rep["positions"] = {}
    for pos in Position:
        key = pos.value
        cols = {name: [] for name in PER_PLAYER}
        for s in stats:
            for j, p in enumerate(s["positions"]):
                if p == key:
                    for name in PER_PLAYER:
                        cols[name].append(s[name][j])
        if not cols["distance"]:
            continue
        td, hid, spr = POSITION_TARGETS[key]
        rep["positions"][key] = {
            "n": len(cols["distance"]),
            "distance": describe(cols["distance"], td),
            "hid": describe(cols["hid"], hid),
            "sprint": describe(cols["sprint"], spr)
            | ({"tolerance_m": GK_SPRINT_TOLERANCE_M} if key == "GK" else {}),
            "sprints_per_98": describe(cols["sprints_per_98"], SPRINT_COUNT_TARGETS.get(key)),
            "hdec_per_98": describe(cols["hdec_per_98"], HIGH_DECEL_TARGETS.get(key)),
            "top_speed": describe(cols["top_speed"], TOP_SPEED_TARGETS.get(key))
            | {"max": float(np.max(cols["top_speed"]))},
            "observed_distance": describe(cols["observed_distance"], td),
        }

    rep["team"] = {}
    for name, (target, sd) in TEAM_TARGETS.items():
        totals = [sum(s[name][11 * k : 11 * k + 11]) for s in stats for k in (0, 1)]
        rep["team"][name] = describe(totals, target) | {"target_sd": sd}
    totals = [sum(s["observed_distance"][11 * k : 11 * k + 11]) for s in stats for k in (0, 1)]
    rep["team"]["observed_distance"] = describe(totals, TEAM_TARGETS["distance"][0])

    rep["phase"] = {
        n: describe([s["phase"][n] for s in stats], t) for n, t in PHASE_TARGETS.items()
    }
    rep["phase_hid"] = {
        n: describe([s["phase_hid"][n] for s in stats], t) for n, t in PHASE_HID_TARGETS.items()
    }

    total = Counter()
    for s in stats:
        total.update(s["purposes"])
    runs = sum(s["runs"] for s in stats)
    rep["runs_per_match"] = runs / len(stats)
    rep["purposes"] = {
        p.value: {
            "per_match": total[p.value] / len(stats),
            "pct": 100.0 * total[p.value] / max(runs, 1),
            "target_pct": PURPOSE_TARGETS.get(p.value),
        }
        for p in RunPurpose
    }

    rep["bands"] = {}
    for key, labels in (("speed_s", SPEED_LABELS), ("accel_s", ACCEL_LABELS)):
        for group in ("outfield", "GK"):
            entry = {"labels": labels, "synthetic_pct": band_pct(stats, key, group)}
            if idsse:
                entry["idsse_pct"] = band_pct(idsse, key, group)
            rep["bands"][f"{key}_{group}"] = entry
    rep["spacing"] = spacing.summarise([s["spacing"] for s in stats])
    if idsse:
        from secondwind.sim.idsse import position_means

        rep["idsse_matches"] = [m["match_id"] for m in idsse]
        rep["idsse_positions"] = position_means(idsse)
        cached = spacing.idsse_measures(cached_only=True)
        if cached:
            rep["idsse_spacing"] = spacing.summarise(cached)
    return rep


def _ms(d: dict, fmt: str = "8.1f") -> str:
    return f"{d['mean']:{fmt}} ± {d['sd']:{fmt.replace('8', '6')}}"


def _off(d: dict, tol: float | None = None, se: bool = False) -> str:
    if "off_pct" not in d:
        return ""
    if "tolerance_m" in d:  # judged in metres, not in %
        off = d["mean"] - d["target"]
        flag = " ok" if abs(off) <= d["tolerance_m"] else " !!"
        err = f" ±{d['se_pct'] * d['target'] / 100:.1f}" if se else ""
        return f"{off:+5.1f} m{err}{flag}"
    flag = "" if tol is None else (" ok" if abs(d["off_pct"]) <= 100 * tol else " !!")
    err = f" ±{d['se_pct']:.1f}" if se else ""
    return f"{d['off_pct']:+6.1f}%{err}{flag}"


def format_report(rep: dict) -> str:
    lines = [f"{rep['n']} matches. Mean ± SD across matches; '!!' = outside the tolerance."]
    lines.append("")
    lines.append(f"  {'match figure':<20}{'mean ± SD':>17}{'target':>9}")
    for key, d in rep["match"].items():
        target = d.get("target", "")
        lines.append(f"  {key:<20}{_ms(d):>17}{target:>9}")

    lines.append("")
    lines.append("  Movement by position (truth: noise-free), per player per match. ±5% tolerance;")
    lines.append("  'off' is the mean against the target ± its standard error. GK >7 m/s: ±5 m.")
    lines.append(
        f"  {'pos':<4}{'distance m':>18}{'off':>16}{'>5.5 m/s':>17}{'off':>16}"
        f"{'>7 m/s':>16}{'off':>17}{'top m/s (target) max':>24}"
    )
    for key, d in rep["positions"].items():
        top = d["top_speed"]
        top_t = f"({top['target']:.2f})" if "target" in top else "(–)"
        lines.append(
            f"  {key:<4}{_ms(d['distance']):>18}{_off(d['distance'], POSITION_TOLERANCE, True):>16}"
            f"{_ms(d['hid']):>17}{_off(d['hid'], POSITION_TOLERANCE, True):>16}"
            f"{_ms(d['sprint']):>16}{_off(d['sprint'], POSITION_TOLERANCE, True):>17}"
            f"{top['mean']:>10.2f} {top_t:>7} {top['max']:.2f}"
        )
    lines.append("")
    lines.append("  Efforts per 98 min (observed, smoothed) [Castellano2025, Table 3]; ±30%.")
    lines.append("  IDSSE columns: same pipeline, full-match players (Bundesliga, TRACAB).")
    lines.append(
        f"  {'pos':<4}{'sprints':>16}{'target':>8}{'off':>10}{'IDSSE':>7}{'high decels':>18}"
        f"{'target':>8}{'IDSSE':>7}{'observed distance':>20}{'IDSSE':>7}"
    )
    ref = rep.get("idsse_positions", {})
    for key, d in rep["positions"].items():
        s, h = d["sprints_per_98"], d["hdec_per_98"]
        r = ref.get(key)
        lines.append(
            f"  {key:<4}{_ms(s):>16}{s.get('target', '–'):>8}{_off(s, 0.30):>10}"
            f"{r['sprints_per_98'] if r else 0:>7.1f}"
            f"{_ms(h):>18}{h.get('target', '–'):>8}{r['hdec_per_98'] if r else 0:>7.1f}"
            f"{d['observed_distance']['mean']:>9.0f} ({_off(d['observed_distance'])})"
            f"{r['distance'] if r else 0:>7.0f}"
        )

    lines.append("")
    lines.append("  Team totals per match (truth) [Allen2025, Figs 2–3].")
    for name, d in rep["team"].items():
        sd = f" ± {d['target_sd']}" if "target_sd" in d else ""
        lines.append(f"  {name:<20}{_ms(d, '9.0f'):>21}  target {d['target']}{sd}  {_off(d)}")

    lines.append("")
    lines.append("  Running by phase, m/min per player slot (GK included) [Allen2026b, Table 5].")
    for name, d in rep["phase"].items():
        lines.append(f"  {name:<20}{_ms(d):>17}{d['target']:>9}{_off(d, PHASE_TOLERANCE):>12}")
    lines.append("  >5.5 m/s by phase, m/min per player slot.")
    for name, d in rep["phase_hid"].items():
        lines.append(f"  {name:<20}{_ms(d):>17}{d['target']:>9}{_off(d, PHASE_TOLERANCE):>12}")

    lines.append("")
    lines.append(
        f"  High-intensity runs (>{P.HI_SPEED} m/s for ≥{P.HI_MIN_S} s): "
        f"{rep['runs_per_match']:.0f} per match, {rep['runs_per_match'] / 22:.1f} per player."
    )
    for name, d in rep["purposes"].items():
        target = f"  peak target {d['target_pct']}%" if d["target_pct"] else ""
        lines.append(f"  {name:<20}{d['per_match']:>8.1f} per match {d['pct']:>6.1f}%{target}")

    lines.append("")
    lines.append("  Time in band, % of player time (observed, smoothed).")
    if "idsse_matches" in rep:
        lines.append(f"  IDSSE: {len(rep['idsse_matches'])} matches, same pipeline at 10 Hz.")
    for key, band in rep["bands"].items():
        syn = band["synthetic_pct"]
        ids = band.get("idsse_pct")
        lines.append(f"  {key}")
        for k, label in enumerate(band["labels"]):
            row = f"    {label:<8}{syn[k]:>7.2f}"
            if ids is not None:
                diff = syn[k] - ids[k]
                ok = (
                    ""
                    if not key.startswith("speed")
                    else (" ok" if abs(diff) <= BAND_TOLERANCE else " !!")
                )
                row += f"   IDSSE {ids[k]:>6.2f}   {diff:+6.2f} pp{ok}"
            lines.append(row)

    lines.append("")
    lines.append("  Spacing (truth: noise-free; sim.spacing). IDSSE: mean of its matches.")
    lines.append(spacing.format_table(rep["spacing"], rep.get("idsse_spacing")))
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m secondwind.sim.batch", description=__doc__)
    parser.add_argument("--seeds", default="1-10", help="e.g. 1-30 or 1,3,5 (default 1-10)")
    parser.add_argument("--jobs", type=int, help="worker processes (default: one per seed)")
    parser.add_argument("--json", type=Path, help="also write the report to this JSON file")
    parser.add_argument(
        "--idsse", action="store_true", help="compare bands with IDSSE (needs sim.idsse first)"
    )
    args = parser.parse_args(argv)
    idsse = None
    if args.idsse:
        from secondwind.sim.idsse import load_derived

        idsse = load_derived() or None
        if idsse is None:
            print("No derived IDSSE files: run python -m secondwind.sim.idsse first.\n")
    rep = build_report(run_batch(parse_seeds(args.seeds), args.jobs), idsse)
    print(format_report(rep))
    if args.json:
        args.json.write_text(json.dumps(rep, indent=1))


if __name__ == "__main__":
    main()
