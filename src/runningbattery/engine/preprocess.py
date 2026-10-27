"""Positions to speed and acceleration, with the generator's pipeline
(``sim.summary.smooth`` and ``kinematics``): dropouts filled by linear interpolation, a zero-lag
4th-order Butterworth low-pass at 1 Hz, central differences for speed and tangential acceleration
[Deutsch2025, Methods]. Frames above the speed or acceleration caps are tracking errors; they are
filled by interpolating the player's speed and acceleration over time.

Every player who played gets a column; it is NaN while they are off the pitch. On and off times
come from the metadata (starters and ``substitutions``), not from the tracking, so a dropout does
not count as leaving the pitch.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from runningbattery.engine import params as P
from runningbattery.io import Match
from runningbattery.sim.summary import kinematics, smooth


@dataclass(frozen=True)
class Tracks:
    """10 Hz kinematics of a whole match, both periods on one frame axis."""

    ids: list[str]  # every player who played, starters first, in metadata order
    period: np.ndarray  # (frames,)
    t: np.ndarray  # (frames,) seconds since the period's kick-off
    alive: np.ndarray  # (frames,) ball in play
    speed: np.ndarray  # (frames, players) m/s, NaN off the pitch
    accel: np.ndarray  # (frames, players) m/s², NaN off the pitch

    @property
    def on(self) -> np.ndarray:
        return ~np.isnan(self.speed)

    @property
    def whole_second(self) -> np.ndarray:
        """Frames that fall on a whole second of their period (the 1 Hz output grid)."""
        return np.round(self.t * P.FRAME_RATE_HZ).astype(int) % round(P.FRAME_RATE_HZ) == 0


def on_pitch(match: Match, ids: list[str], period: np.ndarray, t: np.ndarray) -> np.ndarray:
    """(frames, players) True while each player is on the pitch: starters from kick-off,
    substitutes from the moment they come on, until they go off (same rule as the generator's
    spells: on at the substitution's time, off from it)."""
    start = {p.id: (1, 0.0) for team in match.metadata.teams for p in team.players if p.starter}
    stop: dict[str, tuple[int, float]] = {}
    for sub in match.metadata.substitutions:
        stop[sub.player_out] = (sub.period, sub.t)
        start[sub.player_in] = (sub.period, sub.t)
    out = np.zeros((len(period), len(ids)), dtype=bool)
    key = period * 1e6 + t  # (period, t) in one sortable number
    for j, pid in enumerate(ids):
        a = start[pid]
        b = stop.get(pid, (3, 0.0))
        out[:, j] = (key >= a[0] * 1e6 + a[1]) & (key < b[0] * 1e6 + b[1])
    return out


def _fill(values: np.ndarray) -> np.ndarray:
    """Interpolate NaN frames over time, per column."""
    out = values.copy()
    k = np.arange(len(values))
    for j in range(values.shape[1]):
        col = out[:, j]
        ok = ~np.isnan(col)
        if ok.any() and not ok.all():
            out[:, j] = np.interp(k, k[ok], col[ok])
    return out


def tracks(match: Match) -> Tracks:
    meta = match.metadata
    played = {sub.player_in for sub in meta.substitutions}
    ids = [p.id for team in meta.teams for p in team.players if p.starter or p.id in played]
    col = {pid: j for j, pid in enumerate(ids)}
    frames = match.frames
    xy = np.full((len(frames), len(ids), 2), np.nan)
    for k, f in enumerate(frames):
        for p in f.players:
            xy[k, col[p.id]] = (p.x, p.y)
    period = np.array([f.period for f in frames])
    t = np.array([f.t for f in frames])
    alive = np.array([f.ball_status == "alive" for f in frames])
    speed = np.full((len(frames), len(ids)), np.nan)
    accel = np.full_like(speed, np.nan)
    for p in sorted(set(period.tolist())):
        rows = period == p
        seen = ~np.isnan(xy[rows, :, 0]).all(axis=0)  # players tracked in this period
        v, a = kinematics(smooth(xy[rows][:, seen]))
        speed[np.ix_(rows, seen)] = _fill(v)
        accel[np.ix_(rows, seen)] = _fill(a)
    off = ~on_pitch(match, ids, period, t)
    speed[off] = np.nan
    accel[off] = np.nan
    return Tracks(ids, period, t, alive, speed, accel)
