"""Movement at 10 Hz: team-shape targets and the motion model.

Each player heads for a target point at a wanted speed (set by their role, see ``roles.py``).
The motion model is dv/dt = α(V·n − v) [Narizuka2023, Eq. 3]: n points at the target, α = A0/S0
and V = S0 at full effort (synthesis §4.10). Speeding up is capped by the player's own profile,
a_max(v) = A0·(1 − v/S0) [Morin2021, p.2]; braking by ``BRAKE_MAX``, turning by ``TURN_MAX``, and
speed by S0. At full effort straight ahead the model and the cap agree: α(S0 − v) = a_max(v).

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


def a_max(speed: np.ndarray, a0: np.ndarray, s0: np.ndarray) -> np.ndarray:
    """The most a player can speed up at ``speed``, m/s² [Morin2021, p.2]."""
    return np.maximum(a0 * (1.0 - speed / s0), 0.0)


def step(
    pos: np.ndarray,
    vel: np.ndarray,
    target: np.ndarray,
    speed_cap: np.ndarray,
    a0: np.ndarray,
    s0: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Advance every player one frame towards its target. All arrays are per player.

    ``speed_cap`` is the wanted speed V (at most S0). Near the target V falls to gap / τ, so
    players arrive without overshooting (``ARRIVE_TAU``).
    """
    gap = target - pos
    dist = np.hypot(gap[:, 0], gap[:, 1])
    want_speed = np.minimum(np.minimum(speed_cap, s0), dist / P.ARRIVE_TAU)
    with np.errstate(invalid="ignore", divide="ignore"):
        heading = np.where(dist[:, None] > 1e-6, gap / dist[:, None], 0.0)
    acc = (a0 / s0)[:, None] * (heading * want_speed[:, None] - vel)

    # Split into the part along the current velocity (speeding up or braking) and the part
    # across it (turning), and cap each.
    speed = np.hypot(vel[:, 0], vel[:, 1])
    with np.errstate(invalid="ignore", divide="ignore"):
        along = np.where(speed[:, None] > 1e-6, vel / speed[:, None], heading)
    a_along = np.einsum("ij,ij->i", acc, along)
    a_across = acc - a_along[:, None] * along
    a_along = np.clip(a_along, -P.BRAKE_MAX, a_max(speed, a0, s0))
    across = np.hypot(a_across[:, 0], a_across[:, 1])
    with np.errstate(invalid="ignore", divide="ignore"):
        a_across *= np.where(across > P.TURN_MAX, P.TURN_MAX / across, 1.0)[:, None]
    vel = vel + (a_along[:, None] * along + a_across) * P.DT

    # Turning adds a little speed in a discrete step: keep the gain within a_max(v) and S0.
    new_speed = np.hypot(vel[:, 0], vel[:, 1])
    limit = np.minimum(s0, speed + a_max(speed, a0, s0) * P.DT)
    with np.errstate(invalid="ignore", divide="ignore"):
        vel = vel * np.where(new_speed > limit, limit / new_speed, 1.0)[:, None]
    return pos + vel * P.DT, vel
