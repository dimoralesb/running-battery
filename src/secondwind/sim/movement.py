"""Simple movement at 10 Hz: team-shape targets and an acceleration-limited step.

Each player heads for a target point. Speeding up is capped by the player's own profile,
a_max(v) = A0·(1 − v/S0) [Morin2021, p.2]; slowing down and turning by ``BRAKE_MAX``; speed by S0.
This is the v0 stand-in for the proper motion model [Narizuka2023] that comes on Friday.

The team-shape helpers work in a team's *attacking frame*: u points at the opponent's goal and
v to the team's left, so x = dir·u and y = dir·v with dir = ±1. Inline numbers (line limits,
goalkeeper position) are our assumption.
"""

from __future__ import annotations

import numpy as np

from secondwind.sim import params as P

EDGE = 0.5  # keep shape targets this far inside the lines (m)


def shape_targets(
    slots: np.ndarray, ball_uv: np.ndarray, in_possession: bool, pressing: bool = False
) -> np.ndarray:
    """Target (u, v) for each of a team's 11 slots, given the ball in the team's frame.

    ``slots`` is (11, 2) from ``params.FORMATION_4231``; row 0 is the goalkeeper.
    """
    shape = P.SHAPE_IN_POSSESSION if in_possession else P.SHAPE_OUT_OF_POSSESSION
    line = shape["line_gain"] * ball_uv[0] + shape["line_offset"]
    if pressing:
        line += P.PRESS_LINE_PUSH
    line = float(np.clip(line, -30.0, 25.0))
    out = np.empty_like(slots)
    out[:, 0] = line + shape["depth"] * slots[:, 0]
    out[:, 1] = shape["width"] * slots[:, 1] + shape["ball_pull"] * ball_uv[1]
    # Goalkeeper: on the goal line's side of the box, drifting with the ball (our assumption).
    out[0, 0] = np.clip(-49.0 + 0.12 * (ball_uv[0] + P.HALF_LENGTH), -51.5, -38.0)
    out[0, 1] = np.clip(0.15 * ball_uv[1], -6.0, 6.0)
    return clip_to_pitch(out)


def clip_to_pitch(points: np.ndarray, edge: float = EDGE) -> np.ndarray:
    lim = np.array([P.HALF_LENGTH - edge, P.HALF_WIDTH - edge])
    return np.clip(points, -lim, lim)


def step(
    pos: np.ndarray,
    vel: np.ndarray,
    target: np.ndarray,
    speed_cap: np.ndarray,
    a0: np.ndarray,
    s0: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Advance every player one frame towards its target. All arrays are per player."""
    gap = target - pos
    dist = np.hypot(gap[:, 0], gap[:, 1])
    want_speed = np.minimum(speed_cap, dist / P.ARRIVE_TAU)
    with np.errstate(invalid="ignore", divide="ignore"):
        heading = np.where(dist[:, None] > 1e-6, gap / dist[:, None], 0.0)
    want_vel = heading * want_speed[:, None]

    speed = np.hypot(vel[:, 0], vel[:, 1])
    speeding_up = want_speed > speed
    a_cap = np.where(speeding_up, np.maximum(a0 * (1.0 - speed / s0), 0.0), P.BRAKE_MAX)
    dv = want_vel - vel
    dv_norm = np.hypot(dv[:, 0], dv[:, 1])
    with np.errstate(invalid="ignore", divide="ignore"):
        scale = np.where(dv_norm > 1e-9, np.minimum(1.0, a_cap * P.DT / dv_norm), 0.0)
    vel = vel + dv * scale[:, None]

    speed = np.hypot(vel[:, 0], vel[:, 1])
    with np.errstate(invalid="ignore", divide="ignore"):
        vel = vel * np.where(speed > s0, s0 / speed, 1.0)[:, None]
    return pos + vel * P.DT, vel
