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


def forecast_hi_run(
    gap: float, want: float, v0: float, a0: float, s0: float, seconds: float, stop: float = 0.0
) -> bool:
    """Whether a run would be a high-intensity run, above ``HI_SPEED`` for at least ``HI_MIN_S``
    (as ``runs.hi_runs`` measures it): ``step`` in one dimension, from ``v0`` m/s towards a
    target ``gap`` metres away that stays put, at wanted speed ``want``, for at most ``seconds``
    or until within ``stop`` metres. For the runs tired players skip, which are never run
    (``Physiology.skipped_runs``). Real targets move, so it is rough: on runs that were made it
    agrees with the measured runs for about 3 decisions in 4 and forecasts as many runs as were
    measured (37% of decisions; our measure, 30 seeds, 2026-10-16)."""
    need = round(P.HI_MIN_S / P.DT)
    x, v, above = 0.0, v0, 0
    for _ in range(round(seconds / P.DT)):
        if gap - x <= stop:
            break
        a = a0 / s0 * (min(want, s0, (gap - x) / P.ARRIVE_TAU) - v)
        a = min(a, a0 * (1.0 - v / s0)) if a > 0 else max(a, -P.BRAKE_MAX)
        v = max(v + a * P.DT, 0.0)
        x += v * P.DT
        above = above + 1 if v > P.HI_SPEED else 0
        if above >= need:
            return True
    return False


def _too_close(
    points: np.ndarray, team_of: np.ndarray, team_keep: float, opp_keep: float
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Pairs (i, j) closer than ``team_keep`` (team-mates) or ``opp_keep`` (opponents): how much
    closer (m) and the unit vector from j to i. Two points on exactly the same spot split along
    x, the lower index going left."""
    gap = points[:, None, :] - points[None, :, :]
    dist = np.hypot(gap[..., 0], gap[..., 1])
    same = team_of[:, None] == team_of[None, :]
    keep = np.where(same, team_keep, opp_keep)
    short = np.maximum(keep - dist, 0.0)
    np.fill_diagonal(short, 0.0)
    i, j = np.nonzero(short)
    d = dist[i, j]
    away = np.where(
        d[:, None] > 1e-6,
        gap[i, j] / np.maximum(d, 1e-6)[:, None],
        np.sign(i - j)[:, None] * np.array([1.0, 0.0]),
    )
    return i, j, short[i, j], away


def spread_targets(
    target: np.ndarray,
    team_of: np.ndarray,
    anchored: np.ndarray | None = None,
    keep: float | None = None,
) -> np.ndarray:
    """Team-mates' targets closer than ``keep`` (by default ``SEPARATION_TEAM``) move apart,
    each by half the shortfall (all of it when the other is ``anchored``, which never moves)."""
    keep = P.SEPARATION_TEAM if keep is None else keep
    i, j, short, away = _too_close(target, team_of, keep, 0.0)
    if len(i) == 0:
        return target
    fixed = np.zeros(len(target), dtype=bool) if anchored is None else anchored
    share = np.where(fixed[i], 0.0, np.where(fixed[j], 1.0, 0.5))
    out = target.copy()
    np.add.at(out, i, (share * short)[:, None] * away)
    return clip_to_pitch(out)


def _closest_approach(
    pos: np.ndarray, vel: np.ndarray, team_of: np.ndarray, keep: float, horizon: float
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Team-mate pairs (i, j) that will come closer than ``keep`` within ``horizon`` seconds at
    their current velocities: how much closer at their closest approach (m), and the unit vector
    from j to i at that moment (sideways for paths that cross). A pair already moving apart is
    judged where it is now."""
    r = pos[:, None, :] - pos[None, :, :]
    w = vel[:, None, :] - vel[None, :, :]
    ww = np.einsum("ijk,ijk->ij", w, w)
    t = np.clip(-np.einsum("ijk,ijk->ij", r, w) / np.maximum(ww, 1e-9), 0.0, horizon)
    miss = r + w * t[..., None]
    dist = np.hypot(miss[..., 0], miss[..., 1])
    short = np.where(team_of[:, None] == team_of[None, :], np.maximum(keep - dist, 0.0), 0.0)
    np.fill_diagonal(short, 0.0)
    i, j = np.nonzero(short)
    d = dist[i, j]
    now = r[i, j]
    now_d = np.hypot(now[:, 0], now[:, 1])
    # Head-on (they would meet exactly): step aside, each to their own right.
    side = np.where(
        now_d[:, None] > 1e-6,
        np.stack([-now[:, 1], now[:, 0]], axis=1) / np.maximum(now_d, 1e-6)[:, None],
        np.sign(i - j)[:, None] * np.array([1.0, 0.0]),
    )
    away = np.where(d[:, None] > 1e-6, miss[i, j] / np.maximum(d, 1e-6)[:, None], side)
    return i, j, short[i, j], away


def push_apart(
    pos: np.ndarray,
    team_of: np.ndarray,
    anchored: np.ndarray | None = None,
    vel: np.ndarray | None = None,
    team_keep: float | None = None,
    wall: np.ndarray | None = None,
) -> np.ndarray:
    """Velocity (m/s) that moves each player away from anyone closer than their separation
    (``team_keep``, by default ``SEPARATION_TEAM``, for team-mates; ``SEPARATION_OPP`` for
    opponents), at most ``SEPARATION_MAX``. Team-mates are judged at their closest approach
    within ``SEPARATION_LOOKAHEAD`` seconds at their ``vel``, so that crossing runs move apart
    in time; opponents where they are now. ``anchored`` (bool) players are not pushed, but
    still push others. Opponents of the ``wall`` (bool) members, anchored or not, are pushed
    off it to ``WALL_CLEAR`` [IFAB2025, Law 13]."""
    keep = P.SEPARATION_TEAM if team_keep is None else team_keep
    push = np.zeros_like(pos)
    if vel is None:
        i, j, short, away = _too_close(pos, team_of, keep, 0.0)
    else:
        i, j, short, away = _closest_approach(pos, vel, team_of, keep, P.SEPARATION_LOOKAHEAD)
    np.add.at(push, i, short[:, None] * away / P.SEPARATION_TAU)
    i, j, short, away = _too_close(pos, team_of, 0.0, P.SEPARATION_OPP)
    np.add.at(push, i, short[:, None] * away / P.SEPARATION_TAU)
    if anchored is not None:
        push[anchored] = 0.0
    if wall is not None:
        keep_off = np.where(wall[None, :] & ~wall[:, None], P.WALL_CLEAR, 0.0)
        i, j, short, away = _too_close(pos, team_of, 0.0, keep_off)
        np.add.at(push, i, short[:, None] * away / P.SEPARATION_TAU)
    size = np.hypot(push[:, 0], push[:, 1])
    push *= np.minimum(1.0, P.SEPARATION_MAX / np.maximum(size, 1e-9))[:, None]
    return push


def step(
    pos: np.ndarray,
    vel: np.ndarray,
    target: np.ndarray,
    speed_cap: np.ndarray,
    a0: np.ndarray,
    s0: np.ndarray,
    calm: np.ndarray | None = None,
    push: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Advance every player one frame towards its target. All arrays are per player.

    ``speed_cap`` is the wanted speed V (at most S0). Near the target V falls to gap / τ, so
    players arrive without overshooting (``ARRIVE_TAU``). ``calm`` (bool) marks players not on
    a run or a ball role: they use the gentler ``CALM_ALPHA`` and ``CALM_ARRIVE_TAU``. ``push``
    (from ``push_apart``) is added to the wanted velocity, before the caps; it never raises the
    wanted speed above the larger of the two.
    """
    gap = target - pos
    dist = np.hypot(gap[:, 0], gap[:, 1])
    calm = np.zeros(len(pos), dtype=bool) if calm is None else calm
    arrive = np.where(calm, P.CALM_ARRIVE_TAU, P.ARRIVE_TAU)
    want_speed = np.minimum(np.minimum(speed_cap, s0), dist / arrive)
    with np.errstate(invalid="ignore", divide="ignore"):
        heading = np.where(dist[:, None] > 1e-6, gap / dist[:, None], 0.0)
    want = heading * want_speed[:, None]
    if push is not None:
        # The push turns or slows a moving player but never makes them faster than they want.
        most = np.maximum(want_speed, np.hypot(push[:, 0], push[:, 1]))
        want = want + push
        size = np.hypot(want[:, 0], want[:, 1])
        want *= np.minimum(1.0, most / np.maximum(size, 1e-9))[:, None]
    alpha = a0 / s0 * np.where(calm, P.CALM_ALPHA, 1.0)
    acc = alpha[:, None] * (want - vel)

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
