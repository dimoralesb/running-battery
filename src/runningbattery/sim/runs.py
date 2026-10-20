"""High-intensity runs and their purpose, for ``truth.json``.

A high-intensity run is a spell above 5.5 m/s (19.8 km/h) lasting at least 1 s [Ju2022, p.974],
found on the noise-free positions. Its purpose is the one behind most of the run's frames
(``roles.py``), as a video coder would label the main purpose of an action [Ju2022, p.974]. A run
with no recorded purpose (a loose-ball chase, a restart taker) is ``other``.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from runningbattery.schema import RunPurpose
from runningbattery.sim import params as P
from runningbattery.sim.roles import PURPOSES


@dataclass(frozen=True)
class HiRun:
    player: int  # engine index 0–21
    t_start: float  # s since the period's kick-off
    t_end: float
    purpose: RunPurpose


def speeds(pos: np.ndarray) -> np.ndarray:
    """(n − 1, players) speed between consecutive 10 Hz frames, m/s."""
    return np.hypot(*np.diff(pos, axis=0).transpose(2, 0, 1)) * P.FRAME_RATE_HZ


def spells(above: np.ndarray, min_frames: int) -> list[tuple[int, int]]:
    """(start, stop) index pairs of True spells at least ``min_frames`` long (stop exclusive)."""
    edges = np.diff(np.concatenate([[0], above.astype(np.int8), [0]]))
    starts, stops = np.flatnonzero(edges == 1), np.flatnonzero(edges == -1)
    keep = stops - starts >= min_frames
    return list(zip(starts[keep].tolist(), stops[keep].tolist(), strict=True))


def hi_runs(pos: np.ndarray, purpose: np.ndarray) -> list[HiRun]:
    """High-intensity runs of one period, ordered by start time then player."""
    speed = speeds(pos)
    min_frames = round(P.HI_MIN_S * P.FRAME_RATE_HZ)
    found = []
    for j in range(speed.shape[1]):
        for a, b in spells(speed[:, j] > P.HI_SPEED, min_frames):
            codes = purpose[a:b, j]
            codes = codes[codes >= 0]
            why = PURPOSES[np.bincount(codes).argmax()] if len(codes) else RunPurpose.OTHER
            found.append(HiRun(j, a / P.FRAME_RATE_HZ, b / P.FRAME_RATE_HZ, why))
    return sorted(found, key=lambda r: (r.t_start, r.player))
