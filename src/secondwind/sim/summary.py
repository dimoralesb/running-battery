"""Print a match summary: ``python -m secondwind.sim.summary data/synthetic/m0001``.

Match length, ball in play, possession, event counts against the interim targets, and per-player
distance and top speed. Speeds are plain frame-to-frame differences at 10 Hz: fine for today's
noise-free positions, not for noisy ones (the estimator filters first, synthesis §3.1).
"""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from secondwind.io import Match, read_match
from secondwind.schema import EventType, Phase

RESTARTS = {"kick_off", "throw_in", "goal_kick", "corner", "free_kick"}

# Interim per-match targets until the Wyscout fit on Sunday: (value, source).
TARGETS: dict[str, tuple[float, str]] = {
    "match_minutes": (99.5, "Allen2025, Table 2 (± 2.9)"),
    "ball_in_play_pct": (55.0, "Kavanagh2024, p.80; Allen2026b, Table 2 (accept 50–63)"),
    "passes": (740, "Bassek2025, Fig. 3, approx. (open play)"),
    "shots": (24.4, "Bassek2025, p.6"),
    "duels": (200, "Bassek2025, Fig. 3, approx."),
    "fouls": (22, "Bassek2025, Fig. 3, approx."),
    "throw_ins": (39, "Bassek2025, Fig. 3, approx."),
    "corners": (7.6, "Bassek2025, Fig. 3, approx."),
    "transitions": (50, "Bortnik2022, Tables 1–2 (± 11)"),
}
BALL_IN_PLAY_BAND = (50.0, 63.0)  # [Kavanagh2024, p.80; Allen2026b, Table 2]
POSSESSION_BAND = (40.0, 64.0)  # [Allen2026b, Table 2]
COUNT_TOLERANCE = 0.30  # our test tolerance on event counts


@dataclass(frozen=True)
class Summary:
    match_minutes: float
    ball_in_play_pct: float
    possession_pct: dict[str, float]
    counts: dict[str, int]
    transition_s: float  # mean span of the events labelled as a transition (approx.)
    distance_m: dict[str, float]
    top_speed: dict[str, float]  # m/s
    max_step_speed: float  # fastest frame-to-frame speed of any player, m/s
    positions: dict[str, str]
    extent: dict[str, float]  # largest |x|, |y| reached by players and the ball; ball z range


def event_counts(match: Match) -> dict[str, int]:
    events = match.events
    by_type = Counter(e.type.value for e in events)
    by_subtype = Counter(e.subtype for e in events if e.type == EventType.PASS)
    open_play = sum(n for sub, n in by_subtype.items() if sub not in RESTARTS)
    transitions = {e.possession_id for e in events if e.phase == Phase.POSITIVE_TRANSITION}
    counts = {
        "passes": open_play,
        "shots": by_type["shot"],
        "duels": by_type["duel"],
        "fouls": by_type["foul"],
        "throw_ins": by_subtype["throw_in"],
        "corners": by_subtype["corner"],
        "transitions": len(transitions),
        "goals": by_type["goal"],
        "crosses": by_subtype["cross"],
        "free_kicks": by_subtype["free_kick"],
        "goal_kicks": by_subtype["goal_kick"],
        "kick_offs": by_subtype["kick_off"],
    }
    for t in EventType:
        counts.setdefault(f"all_{t.value}", by_type[t.value])
    passes = [e for e in events if e.type == EventType.PASS]
    counts["completed_passes"] = sum(e.outcome == "success" for e in passes)
    return counts


def transition_seconds(match: Match, dead_starts: dict[int, np.ndarray]) -> float:
    """Mean transition length (approx.): from its first event to the next event that is not
    part of it, or to the moment the ball goes dead if that comes first."""
    transition = (Phase.POSITIVE_TRANSITION, Phase.NEGATIVE_TRANSITION)
    spans, current = [], None  # current = (period, possession_id, start t)

    def close(period: int, t: float) -> None:
        dead = dead_starts[period]
        later = dead[dead > current[2]]
        spans.append(min(t, later[0] if len(later) else t) - current[2])

    for e in match.events:
        if e.team_id is None:
            continue
        key = (e.period, e.possession_id)
        if current is not None and (key != current[:2] or e.phase not in transition):
            if e.period == current[0]:
                close(e.period, e.t)
            current = None
        if current is None and e.phase in transition:
            current = (*key, e.t)
    return float(np.mean(spans)) if spans else 0.0


def summarise(folder: Path) -> Summary:
    """Read (and so validate) a match folder, then summarise it."""
    return summarise_match(read_match(folder))


def summarise_match(match: Match) -> Summary:
    meta = match.metadata
    frames = match.frames
    alive = np.array([f.ball_status == "alive" for f in frames])
    holder = np.array([f.possession_team or "" for f in frames])
    held = alive & (holder != "")
    team_ids = [team.id for team in meta.teams]
    possession = {tid: 100.0 * float(np.mean(holder[held] == tid)) for tid in team_ids}

    ids = [p.id for team in meta.teams for p in team.players]
    period = np.array([f.period for f in frames])
    xy = np.full((len(frames), len(ids), 2), np.nan)
    col = {pid: j for j, pid in enumerate(ids)}
    for k, f in enumerate(frames):
        for p in f.players:
            xy[k, col[p.id]] = (p.x, p.y)
    ball = np.array([(f.ball.x, f.ball.y, f.ball.z) for f in frames])
    t = np.array([f.t for f in frames])
    goes_dead = np.flatnonzero(alive[:-1] & ~alive[1:]) + 1
    dead_starts = {p.period: t[goes_dead[period[goes_dead] == p.period]] for p in meta.periods}
    same_period = period[1:] == period[:-1]
    step = np.hypot(*(np.diff(xy, axis=0)).transpose(2, 0, 1))[same_period]
    speed = step * meta.frame_rate_hz
    return Summary(
        match_minutes=sum(p.duration_s for p in meta.periods) / 60.0,
        ball_in_play_pct=100.0 * float(alive.mean()),
        possession_pct=possession,
        counts=event_counts(match),
        transition_s=transition_seconds(match, dead_starts),
        distance_m={pid: float(np.nansum(step[:, j])) for j, pid in enumerate(ids)},
        top_speed={pid: float(np.nanmax(speed[:, j])) for j, pid in enumerate(ids)},
        max_step_speed=float(np.nanmax(speed)),
        positions={p.id: p.position.value for team in meta.teams for p in team.players},
        extent={
            "player_x": float(np.nanmax(np.abs(xy[..., 0]))),
            "player_y": float(np.nanmax(np.abs(xy[..., 1]))),
            "ball_x": float(np.max(np.abs(ball[:, 0]))),
            "ball_y": float(np.max(np.abs(ball[:, 1]))),
            "ball_z_min": float(np.min(ball[:, 2])),
            "ball_z_max": float(np.max(ball[:, 2])),
        },
    )


def format_summary(folder: Path, s: Summary) -> str:
    lines = [f"Match {folder}"]
    lines.append(f"  length {s.match_minutes:.1f} min (target {TARGETS['match_minutes'][0]} ± 2.9)")
    lo, hi = BALL_IN_PLAY_BAND
    lines.append(
        f"  ball in play {s.ball_in_play_pct:.1f}% (target ~55%, accept {lo:.0f}–{hi:.0f})"
    )
    poss = ", ".join(f"{tid} {pct:.1f}%" for tid, pct in s.possession_pct.items())
    lo, hi = POSSESSION_BAND
    lines.append(f"  possession {poss} (each team {lo:.0f}–{hi:.0f}%)")
    lines.append(f"  transitions last ~{s.transition_s:.1f} s on average (target ~10 s)")
    e = s.extent
    lines.append(
        f"  furthest out: players |x| {e['player_x']:.1f}, |y| {e['player_y']:.1f} m; "
        f"ball |x| {e['ball_x']:.1f}, |y| {e['ball_y']:.1f}, z up to {e['ball_z_max']:.1f} m"
    )
    lines.append("")
    lines.append(f"  {'event':<18}{'count':>7}{'target':>9}  source")
    for key, n in s.counts.items():
        if key.startswith("all_"):
            continue
        target, source = TARGETS.get(key, (None, ""))
        shown = "" if target is None else f"{target:g}"
        lines.append(f"  {key:<18}{n:>7}{shown:>9}  {source}")
    others = {k[4:]: n for k, n in s.counts.items() if k.startswith("all_")}
    lines.append("  all types: " + ", ".join(f"{k} {n}" for k, n in others.items() if n))
    lines.append("")
    lines.append(f"  {'player':<8}{'pos':<5}{'distance (m)':>13}{'top speed m/s (km/h)':>24}")
    for pid, dist in s.distance_m.items():
        v = s.top_speed[pid]
        lines.append(f"  {pid:<8}{s.positions[pid]:<5}{dist:>13.0f}{v:>13.2f} ({v * 3.6:.1f})")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m secondwind.sim.summary", description=__doc__)
    parser.add_argument("folder", type=Path)
    args = parser.parse_args(argv)
    print(format_summary(args.folder, summarise(args.folder)))


if __name__ == "__main__":
    main()
