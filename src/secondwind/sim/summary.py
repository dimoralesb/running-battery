"""Print a match summary: ``python -m secondwind.sim.summary data/synthetic/m0001``.

Match length, ball in play, possession, event counts against the interim targets, and per-player
distance, high-speed and sprint distance, and top speed. ``tracking.jsonl`` is noisy, so positions
are first smoothed as in Deutsch2025: dropouts filled by linear interpolation, then a zero-lag
4th-order Butterworth low-pass at 1 Hz (synthesis §3.1). Raw 10 Hz differences of σ = 0.1 m noise
would make a player standing still seem to move at about 1.8 m/s (derived: 10 Hz × 0.1 m × √2 ×
√(π/2)). ``--clean`` reads the noise-free debug copy instead, if the match was generated with
``--clean-copy``.
"""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy.signal import butter, filtfilt

from secondwind.io import Match, read_match
from secondwind.schema import Event, EventType, Phase
from secondwind.sim import params as P
from secondwind.sim.output import read_clean_copy

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
    "offsides": (2.3, "Bassek2025, Fig. 3, approx."),
    "transitions": (50, "Bortnik2022, Tables 1–2 (± 11)"),
    "transition_s": (10.0, "Bortnik2022, Tables 1–2 (positive 10.9, negative 9.3 s)"),
}
BALL_IN_PLAY_BAND = (50.0, 63.0)  # [Kavanagh2024, p.80; Allen2026b, Table 2]
POSSESSION_BAND = (40.0, 64.0)  # [Allen2026b, Table 2]
COUNT_TOLERANCE = 0.30  # our test tolerance on event counts
# Rare events (under 5 a match) are noisier: for 2.3 offsides, the mean of 5 matches varies by
# about ±30% from chance alone (Poisson, derived). Our test tolerance.
RARE_COUNT_TOLERANCE = 0.50
FILTER_HZ, FILTER_ORDER = 1.0, 4  # [Deutsch2025, Methods]; see synthesis §3.1
SPRINT_SPEED = 7.0  # m/s (25.2 km/h) [Allen2024, p.781; synthesis §4.1]


@dataclass(frozen=True)
class Summary:
    match_minutes: float
    ball_in_play_pct: float
    possession_pct: dict[str, float]
    counts: dict[str, int]
    transition_s: float  # mean span of the events labelled as a transition (approx.)
    distance_m: dict[str, float]
    hid_m: dict[str, float]  # above 5.5 m/s (19.8 km/h), sprint included
    sprint_m: dict[str, float]  # above 7 m/s (25.2 km/h)
    top_speed: dict[str, float]  # m/s
    max_step_speed: float  # fastest frame-to-frame speed of any player, m/s
    positions: dict[str, str]
    extent: dict[str, float]  # largest |x|, |y| reached by players and the ball; ball z range


def event_counts(events: list[Event]) -> dict[str, int]:
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
        "offsides": by_type["offside"],
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


def transition_seconds(events: list[Event], dead_starts: dict[int, np.ndarray]) -> float:
    """Mean transition length (approx.): from its first event to the next event that is not
    part of it, or to the moment the ball goes dead if that comes first."""
    transition = (Phase.POSITIVE_TRANSITION, Phase.NEGATIVE_TRANSITION)
    spans, current = [], None  # current = (period, possession_id, start t)

    def close(period: int, t: float) -> None:
        dead = dead_starts[period]
        later = dead[dead > current[2]]
        spans.append(min(t, later[0] if len(later) else t) - current[2])

    for e in events:
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


def smooth(xy: np.ndarray) -> np.ndarray:
    """Fill dropouts (NaN) by linear interpolation, then low-pass filter. ``xy`` is one period,
    (frames, players, 2)."""
    out = xy.copy()
    k = np.arange(len(xy))
    for j in range(xy.shape[1]):
        for axis in (0, 1):
            col = out[:, j, axis]
            ok = ~np.isnan(col)
            if ok.any() and not ok.all():
                out[:, j, axis] = np.interp(k, k[ok], col[ok])
    b, a = butter(FILTER_ORDER, FILTER_HZ, fs=P.FRAME_RATE_HZ)
    return filtfilt(b, a, out, axis=0)


def movement(periods: list[np.ndarray], ids: list[str]) -> dict[str, dict[str, float]]:
    """Distance, high-speed and sprint distance, and top speed per player, from positions
    (one (frames, players, 2) array per period, already smoothed if noisy)."""
    step = np.concatenate([np.hypot(*np.diff(xy, axis=0).transpose(2, 0, 1)) for xy in periods])
    speed = step * P.FRAME_RATE_HZ
    out: dict[str, dict[str, float]] = {}
    for name, keep in (
        ("distance_m", np.ones_like(speed, dtype=bool)),
        ("hid_m", speed > P.HI_SPEED),
        ("sprint_m", speed > SPRINT_SPEED),
    ):
        total = np.where(keep, step, 0.0)
        out[name] = {pid: float(total[:, j].sum()) for j, pid in enumerate(ids)}
    out["top_speed"] = {pid: float(speed[:, j].max()) for j, pid in enumerate(ids)}
    return out


def summarise(folder: Path, clean: bool = False) -> Summary:
    """Read (and so validate) a match folder, then summarise it."""
    clean_pos = None
    if clean:
        data = read_clean_copy(folder)
        clean_pos = [data[f"pos_{p}"] for p in (1, 2) if f"pos_{p}" in data]
    return summarise_match(read_match(folder), clean_pos)


def summarise_match(match: Match, clean_pos: list[np.ndarray] | None = None) -> Summary:
    """Summary of a match; movement from ``clean_pos`` if given, else smoothed tracking."""
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
    if clean_pos is None:
        clean_pos = [smooth(xy[period == p.period]) for p in meta.periods]
    moved = movement(clean_pos, ids)
    return Summary(
        match_minutes=sum(p.duration_s for p in meta.periods) / 60.0,
        ball_in_play_pct=100.0 * float(alive.mean()),
        possession_pct=possession,
        counts=event_counts(match.events),
        transition_s=transition_seconds(match.events, dead_starts),
        distance_m=moved["distance_m"],
        hid_m=moved["hid_m"],
        sprint_m=moved["sprint_m"],
        top_speed=moved["top_speed"],
        max_step_speed=max(moved["top_speed"].values()),
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
    lines.append(
        f"  {'player':<8}{'pos':<5}{'distance (m)':>13}{'>5.5 m/s':>10}{'>7 m/s':>8}"
        f"{'top speed m/s (km/h)':>24}"
    )
    for pid, dist in s.distance_m.items():
        v = s.top_speed[pid]
        lines.append(
            f"  {pid:<8}{s.positions[pid]:<5}{dist:>13.0f}{s.hid_m[pid]:>10.0f}"
            f"{s.sprint_m[pid]:>8.0f}{v:>13.2f} ({v * 3.6:.1f})"
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m secondwind.sim.summary", description=__doc__)
    parser.add_argument("folder", type=Path)
    parser.add_argument(
        "--clean", action="store_true", help="movement from the noise-free debug copy"
    )
    args = parser.parse_args(argv)
    print(format_summary(args.folder, summarise(args.folder, args.clean)))


if __name__ == "__main__":
    main()
