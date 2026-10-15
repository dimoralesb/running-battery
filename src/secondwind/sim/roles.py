"""Role behaviours: where each player is going, how urgently, and why.

Every frame each player gets a target point, a wanted speed and a run purpose (one of the 12
``RunPurpose`` classes of [Ju2022, Table 1], or none). Three layers, the later ones winning:

1. **Team shape** (``movement.shape_targets``), at drift speed, or walking while the ball is dead.
2. **Runs**: decisions with a purpose, a target and an end time.

   - *Shape runs* start when a player is far from their shape target (``SHAPE_RUN_GAP``).
     Out of possession they are recovery runs when the player is not goal-side of the ball,
     otherwise covering. In possession, back players push up the pitch and the others run up in
     support. Going back into shape in possession is not a labelled run.
   - *Triggered runs* start when a team-mate gets the ball or plays a pass: coming short to
     receive, overlaps, breaking into the box, runs in behind, and support runs in a positive
     transition.

3. **Roles on and around the ball**, set fresh every frame: the carrier (run with ball), the
   receiver (move to receive, or a run in behind onto a through ball, or into the box for a
   cross), the nearest defenders closing down the carrier or the receiver, the cover defender,
   the interceptor, loose-ball chasers, and restart takers.

Runs are explicit decisions so that Saturday's fatigue model can veto them (a skipped run).
All the chances, distances and speeds are in ``params.py``; the inline distances (where each
triggered run aims) are our assumption.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

from secondwind.schema import Position, RunPurpose
from secondwind.sim import movement
from secondwind.sim import params as P

if TYPE_CHECKING:
    from secondwind.sim.match import MatchEngine

PURPOSES = list(RunPurpose)
CODE = {purpose: i for i, purpose in enumerate(PURPOSES)}
NO_PURPOSE = -1
GOAL_U = P.HALF_LENGTH
BACKS = (Position.CB, Position.FB, Position.DM)
FORWARDS = (Position.AM, Position.WM, Position.CF)
MIDFIELD = (Position.DM, Position.CM, Position.AM, Position.WM)


@dataclass
class Run:
    purpose: RunPurpose
    t_end: float
    speed: float  # wanted speed as a share of S0
    target: np.ndarray | None = None  # fixed pitch point
    offset_uv: np.ndarray | None = None  # or: this offset from the ball, in the team's frame
    shape: bool = False  # or: the player's shape target; ends once the gap has closed
    onside: bool = False  # keep the target level with the offside line


class Roles:
    def __init__(self, engine: MatchEngine):
        self.e = engine
        self.runs: dict[int, Run] = {}
        self.receiver_purpose = RunPurpose.MOVE_TO_RECEIVE
        pos = engine.positions
        self.is_gk = np.array([p == Position.GK for p in pos])
        self.is_back = np.array([p in BACKS for p in pos])
        self.is_forward = np.array([p in FORWARDS for p in pos])
        self.is_mid = np.array([p in MIDFIELD for p in pos])

    def clear(self) -> None:
        self.runs.clear()

    def start(self, i: int, run: Run) -> None:
        """Every run decision goes through here (Saturday: tired players may skip it)."""
        self.runs[i] = run

    def free(self, i: int) -> bool:
        return i not in self.runs and not self.is_gk[i]

    # --- Triggers ----------------------------------------------------------------------------

    def on_possession_change(self, team: int, t: float) -> None:
        """New team on the ball: old runs end; a positive transition sends support runners."""
        e = self.e
        self.clear()
        if e.transition is None or e.transition[0] != team:
            return
        idx = e.members(team)
        ball_u = e.to_uv(team, e.ball_xy[:2])[0]
        uv = e.to_uv(team, e.pos[idx])
        behind = self.is_mid[idx] & (uv[:, 0] < ball_u)
        order = np.argsort(np.hypot(*(e.pos[idx] - e.ball_xy[:2]).T))
        chosen = [int(idx[j]) for j in order if behind[j]][: P.SUPPORT_RUNNERS]
        rng = e.rng
        for i in chosen:
            side = np.sign(e.to_uv(team, e.pos[i])[1] - e.to_uv(team, e.ball_xy[:2])[1]) or 1.0
            offset = np.array([-rng.uniform(2.0, 6.0), side * rng.uniform(6.0, 12.0)])
            t_end = min(e.transition[1], t + P.RUN_S[1] + 2.0)
            run = Run(RunPurpose.SUPPORT_PLAY, t_end, P.RUN_SPEED, offset_uv=offset, onside=True)
            self.start(i, run)

    def on_touch(self, carrier: int, t: float) -> None:
        """A team-mate has the ball: someone may come short, overlap, or break into the box."""
        e = self.e
        rng = e.rng
        self.runs.pop(carrier, None)
        team = int(e.team_of[carrier])
        idx = [int(i) for i in e.members(team) if i != carrier]
        c_xy = e.pos[carrier]
        c_u, c_v = e.to_uv(team, c_xy)
        if self.is_gk[carrier]:
            return

        # Come short: the nearest free team-mate moves to about 10 m from the carrier.
        if rng.random() < P.SHOW_CHANCE:
            near = [i for i in idx if self.free(i)]
            if near:
                i = min(near, key=lambda j: np.hypot(*(e.pos[j] - c_xy)))
                away = e.pos[i] - c_xy
                d = max(float(np.hypot(*away)), 1e-6)
                perp = np.array([-away[1], away[0]]) / d
                target = c_xy + away / d * rng.uniform(8.0, 12.0) + perp * rng.normal(0.0, 4.0)
                run = Run(RunPurpose.MOVE_TO_RECEIVE, t + rng.uniform(*P.RUN_S), P.SHOW_SPEED)
                run.target, run.onside = e.inside(target), True
                self.start(i, run)

        wide = abs(c_v) > P.BOX_HALF_WIDTH - 6.0
        side = np.sign(c_v) or 1.0
        # Overlap: the full-back on the ball's side, behind it, runs past the wide player.
        if wide and c_u > -P.THIRD and rng.random() < P.OVERLAP_CHANCE:
            for i in idx:
                i_u, i_v = e.to_uv(team, e.pos[i])
                if e.positions[i] == Position.FB and np.sign(i_v) == side and i_u < c_u:
                    if self.free(i):
                        out = min(P.HALF_WIDTH - 2.0 - abs(c_v), 5.0)
                        run = Run(RunPurpose.OVER_UNDERLAP, t + rng.uniform(*P.RUN_S), P.RUN_SPEED)
                        run.offset_uv, run.onside = np.array([12.0, side * out]), True
                        self.start(i, run)
                    break

        # Break into the box: the ball is wide in the final third, ready for a cross.
        if wide and c_u > P.CROSS_ZONE_U:
            spots = {
                Position.CF: (GOAL_U - 6.0, side * 2.0),  # near post
                Position.AM: (GOAL_U - 11.0, -side * 1.0),  # penalty spot
                Position.WM: (GOAL_U - 7.0, -side * 5.0),  # back post (far-side winger)
            }
            for i in idx:
                pos = e.positions[i]
                if pos not in spots or not self.free(i):
                    continue
                if pos == Position.WM and np.sign(e.to_uv(team, e.pos[i])[1]) == side:
                    continue
                if rng.random() < P.BOX_RUN_CHANCE:
                    target = e.to_uv(team, np.array(spots[pos]) + rng.normal(0.0, 1.0, 2))
                    run = Run(RunPurpose.BREAK_INTO_BOX, t + rng.uniform(*P.RUN_S), P.RUN_SPEED)
                    run.target, run.onside = target, True
                    self.start(i, run)

    def on_pass(
        self, t: float, passer: int, receiver: int, through: bool, cross: bool, open_play: bool
    ) -> None:
        """A pass is played: label the receiver's run; forwards near the line may run in behind
        (offside is judged now, when the ball is played, so these runs are legal)."""
        e = self.e
        rng = e.rng
        if through:
            self.receiver_purpose = RunPurpose.RUN_IN_BEHIND
        elif cross:
            self.receiver_purpose = RunPurpose.BREAK_INTO_BOX
        else:
            self.receiver_purpose = RunPurpose.MOVE_TO_RECEIVE
        self.runs.pop(receiver, None)
        if not open_play:
            return
        team = int(e.team_of[passer])
        line = e.offside_line(team, e.pos[passer])
        for i in e.members(team):
            i = int(i)
            if i in (passer, receiver) or not self.is_forward[i] or not self.free(i):
                continue
            i_u, i_v = e.to_uv(team, e.pos[i])
            if line - P.THROUGH_BALL_NEAR_LINE < i_u <= line and rng.random() < P.BEHIND_CHANCE:
                depth = rng.uniform(8.0, 15.0)
                target_uv = np.array([min(line + depth, GOAL_U - 6.0), 0.8 * i_v])
                run = Run(RunPurpose.RUN_IN_BEHIND, t + rng.uniform(*P.RUN_S), P.RUN_SPEED)
                run.target = e.inside(e.to_uv(team, target_uv))
                self.start(i, run)

    # --- Targets -----------------------------------------------------------------------------

    def shape(self) -> tuple[np.ndarray, int | None]:
        """Shape targets for all 22 (pitch xy), and the team taken to be on the ball."""
        e = self.e
        tgt = np.empty((22, 2))
        kick_off = e.mode == "dead" and e.restart.kind == "kick_off"
        holder = e.poss_team if e.poss_team is not None else e.last_team
        for k in (0, 1):
            if kick_off:
                uv = e.kickoff_shape(k)
            else:
                pressing = e.press is not None and e.press[0] == k
                uv = movement.shape_targets(
                    e.slots[k], e.to_uv(k, e.ball_xy[:2]), holder == k, pressing
                )
                if e.transition is not None and e.transition[0] == k:
                    uv[1:, 0] += 8.0
            tgt[e.members(k)] = e.to_uv(k, uv)
        if holder is not None and not kick_off:
            # Attackers hold their shape just onside; runs and roles below may not.
            idx = e.members(holder)[1:]
            uv = e.to_uv(holder, tgt[idx])
            uv[:, 0] = np.minimum(uv[:, 0], self.onside_u(holder))
            tgt[idx] = e.to_uv(holder, uv)
        return tgt, holder

    def onside_u(self, team: int) -> float:
        return self.e.offside_line(team, self.e.ball_xy[:2]) - P.ONSIDE_MARGIN

    def start_shape_runs(self, t: float, shape: np.ndarray, holder: int) -> None:
        e = self.e
        gap_xy = shape - e.pos
        gap = np.hypot(*gap_xy.T)
        for i in np.flatnonzero(gap > P.SHAPE_RUN_GAP):
            i = int(i)
            if not self.free(i):
                continue
            team = int(e.team_of[i])
            gap_u = e.to_uv(team, gap_xy[i])[0]
            urgency = np.clip(
                (gap[i] - P.SHAPE_RUN_GAP) / (P.SHAPE_RUN_FULL - P.SHAPE_RUN_GAP), 0, 1
            )
            speed = P.SHAPE_RUN_MIN + (P.SHAPE_RUN_SPEED - P.SHAPE_RUN_MIN) * float(urgency)
            if team == holder:
                if gap_u < 0.5 * gap[i]:
                    continue  # dropping back into shape with the ball: no labelled run
                purpose = RunPurpose.PUSH_UP_PITCH if self.is_back[i] else RunPurpose.SUPPORT_PLAY
            else:
                ball_u = e.to_uv(team, e.ball_xy[:2])[0]
                not_goal_side = e.to_uv(team, e.pos[i])[0] > ball_u and gap_u < 0
                purpose = RunPurpose.RECOVERY_RUN if not_goal_side else RunPurpose.COVERING
                if not_goal_side:
                    speed = P.SHAPE_RUN_SPEED
            self.start(i, Run(purpose, t + P.SHAPE_RUN_MAX_S, speed, shape=True))

    def goal_side(self, team: int, xy: np.ndarray, metres: float) -> np.ndarray:
        """The point ``metres`` from ``xy`` towards the goal that ``team`` defends."""
        to_goal = self.e.to_uv(team, np.array([-GOAL_U, 0.0])) - xy
        return xy + to_goal / max(float(np.hypot(*to_goal)), 1e-6) * metres

    def targets(self, t: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Target point, wanted speed (m/s) and purpose code for each player this frame."""
        e = self.e
        mode = e.mode
        shape, holder = self.shape()
        tgt = shape.copy()
        frac = np.full(22, P.DEAD_SPEED if mode == "dead" else P.DRIFT_SPEED)
        purpose = np.full(22, NO_PURPOSE, dtype=np.int8)

        if mode != "dead" and holder is not None:
            self.start_shape_runs(t, shape, holder)
            # Attackers caught offside hurry back (their shape target is just onside).
            idx = e.members(holder)[1:]
            beyond = e.to_uv(holder, e.pos[idx])[:, 0] > self.onside_u(holder) + P.ONSIDE_MARGIN
            frac[idx[beyond]] = P.ONSIDE_SPEED
        for i, run in list(self.runs.items()):
            if t >= run.t_end:
                del self.runs[i]
                continue
            team = int(e.team_of[i])
            if run.shape:
                if np.hypot(*(shape[i] - e.pos[i])) < P.SHAPE_RUN_END:
                    del self.runs[i]
                    continue
                target = shape[i]
            elif run.target is not None:
                target = run.target
            else:
                target = e.ball_xy[:2] + e.to_uv(team, run.offset_uv)
            if run.onside:
                uv = e.to_uv(team, target)
                uv[0] = min(uv[0], self.onside_u(team))
                target = e.to_uv(team, uv)
            tgt[i] = movement.clip_to_pitch(target)
            frac[i] = run.speed
            purpose[i] = CODE[run.purpose]

        def role(i: int, target: np.ndarray, speed: float, why: RunPurpose | None) -> None:
            tgt[i] = target
            frac[i] = speed
            purpose[i] = NO_PURPOSE if why is None else CODE[why]

        if mode == "touch":
            c = e.touch.player
            role(
                c,
                e.touch.carry_to,
                min(e.touch.carry_speed / e.s0[c], P.CHASE_SPEED),
                RunPurpose.RUN_WITH_BALL,
            )
            opp_team = 1 - int(e.team_of[c])
            n_press = 2 if e.press is not None and e.press[0] == opp_team else 1
            idx = e.members(opp_team)[1:]
            order = idx[np.argsort(np.hypot(*(e.pos[idx] - e.pos[c]).T))]
            for i in order[:n_press]:
                role(
                    int(i),
                    self.goal_side(opp_team, e.pos[c], P.PRESS_GAP),
                    P.CHASE_SPEED,
                    RunPurpose.CLOSE_DOWN,
                )
            spot = self.goal_side(opp_team, e.pos[c], P.COVER_DEPTH)
            role(int(order[n_press]), spot, P.SHAPE_RUN_SPEED, RunPurpose.COVERING)
        elif mode == "flight":
            f = e.flight
            if f.result in ("intercepted", "clear"):
                role(f.to, f.end, P.CHASE_SPEED, RunPurpose.INTERCEPTION)
            elif f.to >= 0 and f.result in ("complete", "aerial", "offside"):
                role(f.to, f.end, P.CHASE_SPEED, self.receiver_purpose)
                defenders = e.members(1 - int(e.team_of[f.to]))[1:]
                d = np.hypot(*(e.pos[defenders] - f.end).T)
                j = int(np.argmin(d))
                closer = int(defenders[j])
                if f.challenger >= 0:
                    role(f.challenger, f.end, P.CHASE_SPEED, RunPurpose.INTERCEPTION)
                elif d[j] < P.CLOSE_DOWN_REACH:
                    spot = self.goal_side(int(e.team_of[closer]), f.end, P.PRESS_GAP)
                    role(closer, spot, P.CHASE_SPEED, RunPurpose.CLOSE_DOWN)
        elif mode == "loose":
            for k in (0, 1):
                idx = e.members(k)
                d = np.hypot(*(e.pos[idx] - e.loose_point).T)
                for i in idx[np.argsort(d)[:2]]:
                    role(int(i), e.loose_point, P.CHASE_SPEED, None)
        else:
            r = e.restart
            if r.kind == "corner" or (r.kind == "free_kick" and e.to_uv(r.team, r.spot)[0] > 25.0):
                e.set_piece_targets(tgt, r.team)
            role(r.taker, r.spot, 0.7 * P.CHASE_SPEED, None)
        return tgt, frac * e.s0, purpose
