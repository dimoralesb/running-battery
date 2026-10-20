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

``spread_targets``, ``push_apart`` and ``step`` run 600 times a minute for 22 players, so their
loops are compiled with numba (2026-10-17). The kernels do the same arithmetic in the same order
as the numpy versions they replaced (git history before that date), so a seed gives the same
match, file for file (checked on five matches, varied and no-fatigue included). ``params``
values are passed in as arguments: numba would freeze module globals at compile time.
"""

from __future__ import annotations

import math

import numpy as np
from numba import njit

from runningbattery.sim import params as P

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
    line = min(max(float(line), -30.0), 25.0)
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
    depth = min(max(lo + P.GK_DEPTH_SLOPE * (dist - P.GK_DEPTH_FROM), lo), hi)
    spot = goal + to_ball / dist * min(depth, dist)
    if in_possession:
        u = min(max(back_line_u - P.GK_BEHIND_LINE, spot[0]), -P.HALF_LENGTH + P.GK_MAX_OFF)
        spot = np.array([u, 0.5 * spot[1]])
    return spot


def clip_to_pitch(points: np.ndarray, edge: float = EDGE) -> np.ndarray:
    lim = np.array([P.HALF_LENGTH - edge, P.HALF_WIDTH - edge])
    return np.minimum(np.maximum(points, -lim), lim)


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


@njit(cache=True)
def _spread_kernel(target, team_of, fixed, keep):
    """``spread_targets`` in loops (pairs in row-major order, as ``np.add.at``); also whether
    any pair was too close."""
    n = target.shape[0]
    out = target.copy()
    moved = False
    for i in range(n):
        for j in range(n):
            if i == j or team_of[i] != team_of[j]:
                continue
            gx, gy = target[i, 0] - target[j, 0], target[i, 1] - target[j, 1]
            d = math.hypot(gx, gy)
            short = max(keep - d, 0.0)
            if short == 0.0:
                continue
            moved = True
            if d > 1e-6:
                ax, ay = gx / max(d, 1e-6), gy / max(d, 1e-6)
            else:
                ax, ay = _sign(i - j) * 1.0, _sign(i - j) * 0.0
            share = 0.0 if fixed[i] else (1.0 if fixed[j] else 0.5)
            out[i, 0] += share * short * ax
            out[i, 1] += share * short * ay
    return out, moved


def spread_targets(
    target: np.ndarray,
    team_of: np.ndarray,
    anchored: np.ndarray | None = None,
    keep: float | None = None,
) -> np.ndarray:
    """Team-mates' targets closer than ``keep`` (by default ``SEPARATION_TEAM``) move apart,
    each by half the shortfall (all of it when the other is ``anchored``, which never moves)."""
    keep = P.SEPARATION_TEAM if keep is None else keep
    n = len(target)
    fixed = np.zeros(n, dtype=np.bool_) if anchored is None else np.asarray(anchored, np.bool_)
    out, moved = _spread_kernel(
        np.ascontiguousarray(target, dtype=np.float64),
        np.ascontiguousarray(team_of, dtype=np.int64),
        fixed,
        float(keep),
    )
    return clip_to_pitch(out) if moved else target


@njit(cache=True)
def _sign(x: int) -> float:
    return 1.0 if x > 0 else (-1.0 if x < 0 else 0.0)


@njit(cache=True)
def _push_kernel(
    pos, vel, team_of, anchored, wall, look_ahead, keep, horizon, opp_keep, wall_clear, tau, most
):
    """``push_apart`` in loops: the same sums in the same order as the numpy version (pairs in
    row-major order, team-mates, then opponents, then the wall)."""
    n = pos.shape[0]
    push = np.zeros((n, 2))
    # Team-mates: at their closest approach within ``horizon`` (``_closest_approach``), or where
    # they are now (``_too_close``).
    for i in range(n):
        for j in range(n):
            if i == j or team_of[i] != team_of[j]:
                continue
            rx, ry = pos[i, 0] - pos[j, 0], pos[i, 1] - pos[j, 1]
            if look_ahead:
                wx, wy = vel[i, 0] - vel[j, 0], vel[i, 1] - vel[j, 1]
                ww = wx * wx + wy * wy
                t = -(rx * wx + ry * wy) / max(ww, 1e-9)
                t = min(max(t, 0.0), horizon)
                mx, my = rx + wx * t, ry + wy * t
            else:
                mx, my = rx, ry
            d = math.hypot(mx, my)
            short = max(keep - d, 0.0)
            if short == 0.0:
                continue
            if d > 1e-6:
                ax, ay = mx / max(d, 1e-6), my / max(d, 1e-6)
            elif look_ahead:
                now_d = math.hypot(rx, ry)
                if now_d > 1e-6:  # head-on: step aside, each to their own right
                    ax, ay = -ry / max(now_d, 1e-6), rx / max(now_d, 1e-6)
                else:
                    ax, ay = _sign(i - j) * 1.0, _sign(i - j) * 0.0
            else:
                ax, ay = _sign(i - j) * 1.0, _sign(i - j) * 0.0
            push[i, 0] += short * ax / tau
            push[i, 1] += short * ay / tau
    # Opponents, where they are now; then opponents of the wall members, off the wall.
    for stage in range(2 if wall_clear > 0.0 else 1):
        for i in range(n):
            for j in range(n):
                if i == j or team_of[i] == team_of[j]:
                    continue
                k = opp_keep if stage == 0 else (wall_clear if wall[j] and not wall[i] else 0.0)
                gx, gy = pos[i, 0] - pos[j, 0], pos[i, 1] - pos[j, 1]
                d = math.hypot(gx, gy)
                short = max(k - d, 0.0)
                if short == 0.0:
                    continue
                if d > 1e-6:
                    ax, ay = gx / max(d, 1e-6), gy / max(d, 1e-6)
                else:
                    ax, ay = _sign(i - j) * 1.0, _sign(i - j) * 0.0
                push[i, 0] += short * ax / tau
                push[i, 1] += short * ay / tau
        if stage == 0:
            for i in range(n):
                if anchored[i]:
                    push[i, 0] = 0.0
                    push[i, 1] = 0.0
    for i in range(n):
        size = math.hypot(push[i, 0], push[i, 1])
        f = min(1.0, most / max(size, 1e-9))
        push[i, 0] *= f
        push[i, 1] *= f
    return push


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
    n = len(pos)
    return _push_kernel(
        np.ascontiguousarray(pos, dtype=np.float64),
        np.zeros((n, 2)) if vel is None else np.ascontiguousarray(vel, dtype=np.float64),
        np.ascontiguousarray(team_of, dtype=np.int64),
        np.zeros(n, dtype=np.bool_) if anchored is None else np.asarray(anchored, dtype=np.bool_),
        np.zeros(n, dtype=np.bool_) if wall is None else np.asarray(wall, dtype=np.bool_),
        vel is not None,
        float(P.SEPARATION_TEAM if team_keep is None else team_keep),
        float(P.SEPARATION_LOOKAHEAD),
        float(P.SEPARATION_OPP),
        float(P.WALL_CLEAR) if wall is not None else 0.0,
        float(P.SEPARATION_TAU),
        float(P.SEPARATION_MAX),
    )


@njit(cache=True)
def _step_kernel(
    pos, vel, target, speed_cap, a0, s0, calm, push, has_push, calm_tau, tau, calm_alpha,
    brake, turn, dt,
):  # fmt: skip
    """``step`` in a loop over players: the same arithmetic in the same order as the numpy
    version (``einsum`` of two components = x·x + y·y)."""
    n = pos.shape[0]
    new_pos, new_vel = np.empty((n, 2)), np.empty((n, 2))
    for i in range(n):
        gx, gy = target[i, 0] - pos[i, 0], target[i, 1] - pos[i, 1]
        dist = math.hypot(gx, gy)
        arrive = calm_tau if calm[i] else tau
        want_speed = min(min(speed_cap[i], s0[i]), dist / arrive)
        hx, hy = (gx / dist, gy / dist) if dist > 1e-6 else (0.0, 0.0)
        wx, wy = hx * want_speed, hy * want_speed
        if has_push:
            most = max(want_speed, math.hypot(push[i, 0], push[i, 1]))
            wx, wy = wx + push[i, 0], wy + push[i, 1]
            size = math.hypot(wx, wy)
            f = min(1.0, most / max(size, 1e-9))
            wx, wy = wx * f, wy * f
        alpha = a0[i] / s0[i] * (calm_alpha if calm[i] else 1.0)
        ax, ay = alpha * (wx - vel[i, 0]), alpha * (wy - vel[i, 1])
        speed = math.hypot(vel[i, 0], vel[i, 1])
        lx, ly = (vel[i, 0] / speed, vel[i, 1] / speed) if speed > 1e-6 else (hx, hy)
        a_along = ax * lx + ay * ly
        cx, cy = ax - a_along * lx, ay - a_along * ly
        a_max_now = max(a0[i] * (1.0 - speed / s0[i]), 0.0)
        a_along = min(max(a_along, -brake), a_max_now)
        across = math.hypot(cx, cy)
        f = turn / across if across > turn else 1.0
        cx, cy = cx * f, cy * f
        vx = vel[i, 0] + (a_along * lx + cx) * dt
        vy = vel[i, 1] + (a_along * ly + cy) * dt
        new_speed = math.hypot(vx, vy)
        limit = min(s0[i], speed + a_max_now * dt)
        f = limit / new_speed if new_speed > limit else 1.0
        vx, vy = vx * f, vy * f
        new_vel[i, 0], new_vel[i, 1] = vx, vy
        new_pos[i, 0], new_pos[i, 1] = pos[i, 0] + vx * dt, pos[i, 1] + vy * dt
    return new_pos, new_vel


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

    Speeding up is capped at a_max(v), braking at ``BRAKE_MAX`` (the part of the acceleration
    along the current velocity), turning at ``TURN_MAX`` (the part across it); turning adds a
    little speed in a discrete step, so the new speed is kept within a_max(v) and S0.
    """
    n = len(pos)

    def f64(x) -> np.ndarray:
        x = np.asarray(x, dtype=np.float64)
        return x if x.shape[:1] == (n,) else np.broadcast_to(x, (n,) + x.shape[1:]).copy()

    return _step_kernel(
        f64(pos),
        f64(vel),
        f64(target),
        f64(speed_cap),
        f64(a0),
        f64(s0),
        np.zeros(n, dtype=np.bool_) if calm is None else np.asarray(calm, dtype=np.bool_),
        np.zeros((n, 2)) if push is None else f64(push),
        push is not None,
        float(P.CALM_ARRIVE_TAU),
        float(P.ARRIVE_TAU),
        float(P.CALM_ALPHA),
        float(P.BRAKE_MAX),
        float(P.TURN_MAX),
        float(P.DT),
    )
