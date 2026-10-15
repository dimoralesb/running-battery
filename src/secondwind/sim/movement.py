"""Movement at 10 Hz: team-shape targets and the motion model.

Each player heads for a target point at a wanted speed (set by their role, see ``roles.py``).
The motion model is dv/dt = α(V·n − v) [Narizuka2023, Eq. 3]: n points at the target, α = A0/S0
and V = S0 at full effort (synthesis §4.10). Speeding up is capped by the player's own profile,
a_max(v) = A0·(1 − v/S0) [Morin2021, p.2]; braking by ``BRAKE_MAX``, turning by ``TURN_MAX``, and
speed by S0. At full effort straight ahead the model and the cap agree: α(S0 − v) = a_max(v).
Calm movement (holding the shape, repositioning, the ball dead) uses a gentler α and arrival
(``CALM_ALPHA``, ``CALM_ARRIVE_TAU``).

The team shape blends an in-possession and an out-of-possession shape (``SHAPE_SWITCH_S``)
around a lagged copy of the ball (``SHAPE_LAG_S``); front players hold higher without the ball
(``OUT_OF_POSSESSION_HOLD``). The goalkeeper stands on the line from goal to ball, or behind a
high back line when the team has the ball (``keeper_spot``).

The team-shape helpers work in a team's *attacking frame*: u points at the opponent's goal and
v to the team's left, so x = dir·u and y = dir·v with dir = ±1. Inline numbers (line limits,
goalkeeper position) are our assumption.
"""

from __future__ import annotations

import numpy as np

from secondwind.sim import params as P

EDGE = 0.5  # keep shape targets this far inside the lines (m)


def shape_targets(
    slots: np.ndarray,
    ball_uv: np.ndarray,
    in_possession: float,
    pressing: bool = False,
    hold: np.ndarray | None = None,
) -> np.ndarray:
    """Target (u, v) for each of a team's 11 slots, given the ball in the team's frame.

    ``slots`` is (11, 2) from ``params.FORMATION_4231``; row 0 is the goalkeeper.
    ``in_possession`` is the weight of the in-possession shape, 0–1 (``SHAPE_SWITCH_S``).
    ``hold`` (11,) is how much higher each slot stays without the ball
    (``OUT_OF_POSSESSION_HOLD``).
    """
    w = float(in_possession)
    shape = {
        k: w * P.SHAPE_IN_POSSESSION[k] + (1.0 - w) * P.SHAPE_OUT_OF_POSSESSION[k]
        for k in P.SHAPE_IN_POSSESSION
    }
    line = shape["line_gain"] * ball_uv[0] + shape["line_offset"]
    if pressing:
        line += P.PRESS_LINE_PUSH
    line = float(np.clip(line, -30.0, 25.0))
    out = np.empty_like(slots)
    out[:, 0] = line + shape["depth"] * slots[:, 0]
    if hold is not None:
        out[:, 0] += (1.0 - w) * hold
    out[:, 1] = shape["width"] * slots[:, 1] + shape["ball_pull"] * ball_uv[1]
    out[0] = keeper_spot(ball_uv, w > 0.5, float(out[1:, 0].min()))
    return clip_to_pitch(out)


def keeper_spot(ball_uv: np.ndarray, in_possession: bool, back_line_u: float) -> np.ndarray:
    """Goalkeeper's (u, v) (params, "Goalkeeper"): behind a high back line with the ball,
    otherwise on the line from the goal centre to the ball."""
    goal = np.array([-P.HALF_LENGTH, 0.0])
    to_ball = ball_uv - goal
    dist = max(float(np.hypot(*to_ball)), 1e-6)
    lo, hi = P.GK_DEPTH
    depth = float(np.clip(lo + P.GK_DEPTH_SLOPE * (dist - P.GK_DEPTH_FROM), lo, hi))
    spot = goal + to_ball / dist * min(depth, dist)
    if in_possession:
        u = np.clip(back_line_u - P.GK_BEHIND_LINE, spot[0], -P.HALF_LENGTH + P.GK_MAX_OFF)
        spot = np.array([u, 0.5 * spot[1]])
    return spot


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
    calm: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Advance every player one frame towards its target. All arrays are per player.

    ``speed_cap`` is the wanted speed V (at most S0). Near the target V falls to gap / τ, so
    players arrive without overshooting (``ARRIVE_TAU``). ``calm`` (bool) marks players not on
    a run or a ball role: they use the gentler ``CALM_ALPHA`` and ``CALM_ARRIVE_TAU``.
    """
    gap = target - pos
    dist = np.hypot(gap[:, 0], gap[:, 1])
    calm = np.zeros(len(pos), dtype=bool) if calm is None else calm
    arrive = np.where(calm, P.CALM_ARRIVE_TAU, P.ARRIVE_TAU)
    want_speed = np.minimum(np.minimum(speed_cap, s0), dist / arrive)
    with np.errstate(invalid="ignore", divide="ignore"):
        heading = np.where(dist[:, None] > 1e-6, gap / dist[:, None], 0.0)
    alpha = a0 / s0 * np.where(calm, P.CALM_ALPHA, 1.0)
    acc = alpha[:, None] * (heading * want_speed[:, None] - vel)

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
