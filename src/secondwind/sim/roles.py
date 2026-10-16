"""Role behaviours: where each player is going, how urgently, and why.

Every frame each player gets a target point, a wanted speed and a run purpose (one of the 12
``RunPurpose`` classes of [Ju2022, Table 1], or none). Three layers, the later ones winning:

1. **Team shape** (``movement.shape_targets``) around a lagged copy of the ball, plus small
   repositioning moves (``WANDER_*``), at drift speed, or walking while the ball is dead.
2. **Runs**: decisions with a purpose, a target and an end time.

   - *Shape runs* start when a player is far from their shape target (``SHAPE_RUN_GAP``).
     Out of possession they are recovery runs when the player is not goal-side of the ball,
     otherwise covering. In possession, back players push up the pitch and the others run up in
     support. Going back into shape in possession is not a labelled run.
     A recovery run goes up to full effort only when there is danger (``DANGER_U``).
   - *Triggered runs* start when a team-mate gets the ball or plays a pass: coming short to
     receive, exploiting space, midfield support, overlaps, breaking into the box, runs in
     behind (and the defenders who track them), and, in a positive transition, support runs
     and forwards breaking towards goal. Out of possession, a forward or central midfielder
     may close down a new carrier.

3. **Roles on and around the ball**, set fresh every frame: the carrier (run with ball), the
   receiver (move to receive, or a run in behind onto a through ball, or into the box for a
   cross), the nearest defenders closing down the carrier or the receiver, the cover defender,
   the interceptor, the goalkeeper coming for a ball near goal, loose-ball chasers, and restart
   takers. While the ball is dead: opponents keep the legal distance, set pieces (a corner, or a
   free kick near goal) send six attackers and their markers forward, a free kick in range gets
   a wall, and after a goal the scorer's team-mates gather round them.

Each position's run and role speeds are scaled by its work rate (``POSITION_EFFORT``), and in
play by the match tempo (``TEMPO_SD``), which both teams share.

Runs are explicit decisions so that the fatigue model (``physiology.py``) can veto them: a tired
player may skip a hard run, and the runs they make are shorter (``start``); their runs and ball
roles are slower (``targets``). All the chances, distances and speeds are in ``params.py``; the
inline distances (where each triggered run aims) are our assumption.
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
        self.wall_for = None  # the restart the wall below belongs to
        self.wall_members: list[int] = []
        self.plan_for = None  # the set piece the plan below belongs to
        self.plan: list[tuple[int, np.ndarray, bool]] = []
        self.receiver_purpose = RunPurpose.MOVE_TO_RECEIVE
        pos = engine.positions
        self.is_gk = np.array([p == Position.GK for p in pos])
        self.is_back = np.array([p in BACKS for p in pos])
        self.is_forward = np.array([p in FORWARDS for p in pos])
        self.is_mid = np.array([p in MIDFIELD for p in pos])
        self.is_dm = np.array([p == Position.DM for p in pos])  # holds position on a counter
        self.is_cm = np.array([p == Position.CM for p in pos])
        self.is_defender = np.array([p in (Position.CB, Position.FB) for p in pos])
        # Repositioning offsets (params.WANDER_*), from their own generator so that they do not
        # shift the match flow's draws.
        self.wander_rng = np.random.default_rng(int(engine.rng.integers(2**63)))
        self.wander = np.zeros((22, 2))
        self.wander_left = np.zeros(22)
        self.wander_sd = np.array([P.WANDER_SD[p] for p in pos])
        knobs = P.PRE_FATIGUE if engine.pre_fatigue else vars(P)
        self.effort = np.array([knobs["POSITION_EFFORT"][p] for p in pos])
        self.overlap_chance = knobs["OVERLAP_CHANCE"]
        self.mid_support_chance = knobs["MID_SUPPORT_CHANCE"]
        self.tempo = engine.tempo  # None: no shared tempo
        self.is_central_mid = np.array([p in (Position.DM, Position.CM, Position.AM) for p in pos])
        # Players who skipped a run, and until when they are not asked again (``start``).
        self.declined: dict[int, float] = {}

    def clear(self) -> None:
        self.runs.clear()
        self.declined.clear()

    def start(self, i: int, run: Run, t: float) -> None:
        """Every run decision goes through here. With fatigue on, a hard run (wanted speed above
        ``HARD_RUN_SPEED``) is skipped with chance 1 − ``Physiology.run_choice``; the player
        then keeps to their calm movement (a tired player jogs back instead of sprinting) and is
        not asked again until the run's planned end, or for a shape run ``SHAPE_DECLINE_S``.
        Decisions on runs that would have been high-intensity runs (above ``HI_SPEED``) are kept,
        the skipped ones for ``truth.json``. A run that is made lasts ``Physiology.shorten`` of
        its planned time."""
        body = self.e.physiology
        if body is not None:
            rate = self.effort[i] * (1.0 if self.tempo is None else self.tempo)
            want = min(run.speed * rate, 1.0) * self.e.s0[i]
            if want > P.HARD_RUN_SPEED:
                made = body.makes_run(i, run.speed >= P.DECISIVE_EFFORT)
                if want > P.HI_SPEED:
                    body.decide(i, t, run.t_end, run.purpose, made)
                if not made:
                    self.declined[i] = (
                        min(run.t_end, t + P.SHAPE_DECLINE_S) if run.shape else run.t_end
                    )
                    return
                run.t_end = t + (run.t_end - t) * body.shorten(i)
        self.runs[i] = run

    def free(self, i: int) -> bool:
        return i not in self.runs and i not in self.declined and not self.is_gk[i]

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
        behind = self.is_mid[idx] & ~self.is_dm[idx] & (uv[:, 0] < ball_u)
        order = np.argsort(np.hypot(*(e.pos[idx] - e.ball_xy[:2]).T))
        chosen = [int(idx[j]) for j in order if behind[j]][: P.SUPPORT_RUNNERS]
        rng = e.rng
        for i in chosen:
            side = np.sign(e.to_uv(team, e.pos[i])[1] - e.to_uv(team, e.ball_xy[:2])[1]) or 1.0
            offset = np.array([-rng.uniform(2.0, 6.0), side * rng.uniform(6.0, 12.0)])
            t_end = min(e.transition[1], t + rng.uniform(*P.SPRINT_RUN_S))
            run = Run(RunPurpose.SUPPORT_PLAY, t_end, P.COUNTER_SUPPORT_EFFORT, offset_uv=offset)
            run.onside = True
            self.start(i, run, t)
        # Forwards ahead of the ball break towards goal.
        for j, i in enumerate(idx):
            i = int(i)
            if self.is_forward[i] and uv[j, 0] > ball_u and self.free(i):
                if rng.random() < P.COUNTER_RUN_CHANCE:
                    target = uv[j] + np.array([rng.uniform(*P.COUNTER_DEPTH), -0.3 * uv[j, 1]])
                    target[0] = min(target[0], GOAL_U - 8.0)
                    t_end = min(e.transition[1], t + rng.uniform(*P.SPRINT_RUN_S))
                    run = Run(RunPurpose.RUN_IN_BEHIND, t_end, P.BEHIND_EFFORT)
                    run.target = e.inside(e.to_uv(team, target))
                    self.start(i, run, t)

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
        self.press_carrier(carrier, t)

        # Exploit space: a free forward runs into space towards goal.
        forwards = [i for i in idx if self.is_forward[i] and self.free(i)]
        if c_u > -P.THIRD and forwards and rng.random() < P.EXPLOIT_CHANCE:
            i = forwards[int(rng.integers(len(forwards)))]
            i_u, i_v = e.to_uv(team, e.pos[i])
            angle = rng.normal(0.0, 0.6) - 0.01 * i_v
            step = rng.uniform(*P.EXPLOIT_LENGTH) * np.array([np.cos(angle), np.sin(angle)])
            target = e.inside(e.to_uv(team, np.array([i_u, i_v]) + step))
            run = Run(RunPurpose.MOVE_TO_RECEIVE, t + rng.uniform(*P.RUN_S), P.RUN_SPEED)
            run.target, run.onside = target, True
            self.start(i, run, t)

        # Support: a central midfielder well behind the ball runs up behind it.
        if c_u > -P.THIRD:
            for i in idx:
                if not (self.is_central_mid[i] and self.free(i)):
                    continue
                if c_u - e.to_uv(team, e.pos[i])[0] > P.MID_SUPPORT_GAP:
                    if rng.random() < self.mid_support_chance:
                        offset = np.array([-P.MID_SUPPORT_BEHIND, rng.normal(0.0, 6.0)])
                        run = Run(RunPurpose.SUPPORT_PLAY, t + rng.uniform(*P.RUN_S), P.RUN_SPEED)
                        run.offset_uv, run.onside = offset, True
                        self.start(i, run, t)

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
                self.start(i, run, t)

        wide = abs(c_v) > P.BOX_HALF_WIDTH - 6.0
        side = np.sign(c_v) or 1.0
        # Overlap: the full-back on the ball's side, behind it, runs past the wide player.
        if wide and c_u > -P.THIRD and rng.random() < self.overlap_chance:
            for i in idx:
                i_u, i_v = e.to_uv(team, e.pos[i])
                if e.positions[i] == Position.FB and np.sign(i_v) == side and i_u < c_u:
                    if self.free(i):
                        out = min(P.HALF_WIDTH - 2.0 - abs(c_v), 5.0)
                        t_end = t + rng.uniform(*P.SPRINT_RUN_S)
                        run = Run(RunPurpose.OVER_UNDERLAP, t_end, P.OVERLAP_EFFORT)
                        run.offset_uv, run.onside = np.array([12.0, side * out]), True
                        self.start(i, run, t)
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
                    self.start(i, run, t)

    def press_carrier(self, carrier: int, t: float) -> None:
        """The nearest free forward (carrier in their own half) or central midfielder (DM, CM;
        carrier in the middle third, our side of halfway) of the other team, if close enough,
        may close the carrier down (goal-side of the ball)."""
        e = self.e
        team = 1 - int(e.team_of[carrier])
        u = e.to_uv(team, e.pos[carrier])[0]
        if u >= 0.0:
            who, chance = self.is_forward, P.PRESS_RUN_CHANCE
        elif u > -P.THIRD:
            who, chance = self.is_dm | self.is_cm, P.MID_PRESS_CHANCE
        else:
            return
        near = [int(i) for i in e.members(team) if who[i] and self.free(int(i))]
        if not near or e.rng.random() >= chance:
            return
        i = min(near, key=lambda j: float(np.hypot(*(e.pos[j] - e.pos[carrier]))))
        if np.hypot(*(e.pos[i] - e.pos[carrier])) <= P.PRESS_REACH:
            run = Run(RunPurpose.CLOSE_DOWN, t + e.rng.uniform(*P.RUN_S), P.CHASE_SPEED)
            run.offset_uv = np.array([-P.PRESS_GAP, 0.0])
            self.start(i, run, t)

    def on_pass(
        self,
        t: float,
        passer: int,
        receiver: int,
        through: bool,
        cross: bool,
        open_play: bool,
        end: np.ndarray,
    ) -> None:
        """A pass is played: label the receiver's run; forwards near the line may run in behind
        (offside is judged now, when the ball is played, so these runs are legal)."""
        e = self.e
        rng = e.rng
        if through:
            self.receiver_purpose = RunPurpose.RUN_IN_BEHIND
            self.track(t, receiver, end)
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
                depth = rng.uniform(*P.BEHIND_DEPTH)
                target_uv = np.array([min(line + depth, GOAL_U - 6.0), 0.8 * i_v])
                t_end = t + rng.uniform(*P.SPRINT_RUN_S)
                run = Run(RunPurpose.RUN_IN_BEHIND, t_end, P.BEHIND_EFFORT)
                run.target = e.inside(e.to_uv(team, target_uv))
                self.start(i, run, t)
                self.track(t, i, run.target)

    def track(self, t: float, runner: int, aim: np.ndarray) -> None:
        """The defenders (CB, FB) nearest a runner in behind sprint back goal-side of where the
        runner is going (a recovery run)."""
        e = self.e
        team = 1 - int(e.team_of[runner])
        idx = [int(i) for i in e.members(team) if self.is_defender[i] and self.free(int(i))]
        idx.sort(key=lambda i: float(np.hypot(*(e.pos[i] - e.pos[runner]))))
        for i in idx[: P.TRACKERS]:
            run = Run(RunPurpose.RECOVERY_RUN, t + e.rng.uniform(*P.SPRINT_RUN_S), P.TRACK_EFFORT)
            run.target = e.inside(self.goal_side(team, aim, P.TRACK_GOAL_SIDE))
            self.start(i, run, t)

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
                    e.slots[k], e.to_uv(k, e.shape_ball), e.shape_w[k], pressing, e.hold[k]
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
                counter = e.transition is not None and e.transition[0] != team
                if not_goal_side and (ball_u < P.DANGER_U or counter):
                    speed = P.SHAPE_RUN_SPEED + (P.RECOVERY_EFFORT - P.SHAPE_RUN_SPEED) * urgency
            self.start(i, Run(purpose, t + P.SHAPE_RUN_MAX_S, speed, shape=True), t)

    def step_wander(self) -> np.ndarray:
        """This frame's repositioning offsets: a new spot for each player whose time is up."""
        self.wander_left -= P.DT
        due = np.flatnonzero(self.wander_left <= 0.0)
        if len(due):
            rng = self.wander_rng
            self.wander[due] = rng.normal(0.0, 1.0, (len(due), 2)) * self.wander_sd[due, None]
            self.wander_left[due] = rng.uniform(*P.WANDER_S, len(due))
        return self.wander

    def keeper_claim(self, keeper: int, end: np.ndarray) -> np.ndarray | None:
        """Where the keeper goes for a ball landing at ``end``, if it lands within
        ``GK_CLAIM_REACH`` of the goal centre (a cross, or a ball over the top to sweep up)."""
        team = int(self.e.team_of[keeper])
        goal = np.array([-GOAL_U, 0.0])
        gap = self.e.to_uv(team, end) - goal
        dist = float(np.hypot(*gap))
        if dist > P.GK_CLAIM_REACH:
            return None
        return self.e.to_uv(team, goal + gap / max(dist, 1e-6) * max(dist - 1.0, 0.5))

    def keep_distance(self, tgt: np.ndarray) -> None:
        """Opponents keep the legal distance from a restart (``RESTART_DISTANCE``, ``CORNER_ARC``,
        ``THROW_IN_DISTANCE``), plus ``RESTART_MARGIN``. A player inside, or with a target inside,
        heads for the edge on their own side (the shortest way out); at a free kick or corner, a
        player whose straight path would cross the circle walks round its edge instead
        (``RESTART_ARC_STEP``)."""
        e = self.e
        r = e.restart
        keep = {
            "free_kick": P.RESTART_DISTANCE,
            "corner": P.RESTART_DISTANCE + P.CORNER_ARC,
            "throw_in": P.THROW_IN_DISTANCE,
        }.get(r.kind)
        if keep is None:
            return  # kick-offs have their own shape; goal kicks leave the box free anyway
        keep += P.RESTART_MARGIN
        defend = 1 - r.team
        idx = e.members(defend)
        pos, goal = e.pos[idx], tgt[idx]
        side = pos - r.spot
        d = np.hypot(*side.T)
        home = e.to_uv(defend, np.array([-GOAL_U, 0.0])) - r.spot  # towards their own goal
        home /= max(float(np.hypot(*home)), 1e-6)
        away = np.where(d[:, None] > 1e-6, side / np.maximum(d, 1e-6)[:, None], home)
        # Closest point to the ball on the straight path from the player to their target.
        path = goal - pos
        s = np.clip(
            np.einsum("ij,ij->i", r.spot - pos, path) / np.maximum((path**2).sum(1), 1e-9), 0, 1
        )
        crosses = np.hypot(*(pos + s[:, None] * path - r.spot).T) < keep
        crosses &= r.kind != "throw_in"  # 2 m circle on the line: stepping out is enough
        # Clearly inside (not just on the edge, where walking round still works). A wall spot is
        # on the edge itself, so targets get the same 0.1 m.
        step_out = (d < keep - 0.1) | (np.hypot(*(goal - r.spot).T) < keep - 0.1)
        out = r.spot + away * keep
        # Round the edge: a point a little further round, towards the target's side.
        at = np.arctan2(side[:, 1], side[:, 0])
        turn = np.angle(np.exp(1j * (np.arctan2(*(goal - r.spot).T[::-1]) - at)))
        at = at + np.clip(turn, -P.RESTART_ARC_STEP, P.RESTART_ARC_STEP)
        round_edge = r.spot + keep * np.stack([np.cos(at), np.sin(at)], axis=1)
        new = np.where(step_out[:, None], out, np.where(crosses[:, None], round_edge, goal))
        tgt[idx] = movement.clip_to_pitch(new)

    def wall(self, set_piece: bool) -> list[tuple[int, np.ndarray]]:
        """A free kick in range: the defenders and their spots in a wall (``WALL_*``), side by
        side. The members are the free defenders nearest the wall when the free kick is first
        set up, kept until it is taken, and ordered along the wall as they come in."""
        e = self.e
        r = e.restart
        defend = 1 - r.team
        to_goal = e.to_uv(defend, np.array([-GOAL_U, 0.0])) - r.spot
        dist = float(np.hypot(*to_goal))
        if dist > P.WALL_RANGE:
            return []
        n = P.WALL_SIZE[1] if dist < P.WALL_NEAR else P.WALL_SIZE[0]
        unit = to_goal / max(dist, 1e-6)
        across = np.array([-unit[1], unit[0]])
        centre = r.spot + unit * min(P.RESTART_DISTANCE + P.RESTART_MARGIN, dist - 1.0)
        spots = centre + np.outer(np.arange(n) - (n - 1) / 2.0, across) * P.WALL_GAP
        if self.wall_for is not r:
            markers = set(int(e.members(defend)[s]) for s in P.BOX_MARKERS) if set_piece else set()
            free = [int(i) for i in e.members(defend)[1:] if int(i) not in markers]
            free.sort(key=lambda j: float(np.hypot(*(e.pos[j] - centre))))
            members = free[:n]
            members.sort(key=lambda j: float((e.pos[j] - centre) @ across))
            self.wall_for, self.wall_members = r, members
        return list(zip(self.wall_members, spots, strict=True))

    def wall_mask(self) -> np.ndarray | None:
        """The wall members while their free kick is waiting (for ``movement.push_apart``)."""
        e = self.e
        if e.mode != "dead" or self.wall_for is not e.restart:
            return None
        mask = np.zeros(22, dtype=bool)
        mask[self.wall_members] = True
        return mask

    def keep_off_wall(self, tgt: np.ndarray, spots: list[np.ndarray]) -> None:
        """Attackers' targets at least ``WALL_CLEAR`` from the wall [IFAB2025, Law 13]: a target
        too close moves straight out from the wall (towards the ball if it is on it)."""
        e = self.e
        r = e.restart
        a, b = spots[0], spots[-1]
        idx = np.array([i for i in e.members(r.team) if i != r.taker])
        p = tgt[idx]
        ab = b - a
        s = np.clip((p - a) @ ab / max(float(ab @ ab), 1e-9), 0.0, 1.0)
        near = a + s[:, None] * ab
        off = p - near
        d = np.hypot(*off.T)
        to_ball = r.spot - (a + b) / 2.0
        to_ball /= max(float(np.hypot(*to_ball)), 1e-6)
        away = np.where(d[:, None] > 1e-6, off / np.maximum(d, 1e-6)[:, None], to_ball)
        tgt[idx] = np.where(d[:, None] < P.WALL_CLEAR, near + away * P.WALL_CLEAR, p)

    def huddle(self, h, t: float, role, anchored: np.ndarray) -> None:
        """After a goal: the scorer jogs to their spot; the team-mates gather round them, at
        spots spread evenly round a ring, centred on the side they come from and taken in the
        order they come, so that nobody has to cross. Once they have all arrived, the huddle
        holds ``HUDDLE_HOLD_S``."""
        e = self.e
        near = np.hypot(*(e.pos[h.mates] - e.pos[h.scorer]).T) < P.HUDDLE_RING + 0.3
        if not h.formed and near.all():
            h.formed = True
            h.t_end = min(h.t_end, t + P.HUDDLE_HOLD_S)
        role(h.scorer, h.spot, P.WALL_SPEED, None)
        anchored[h.scorer] = True
        at = e.pos[h.scorer]
        off = e.pos[h.mates] - at
        base = np.arctan2(*off.sum(axis=0)[::-1])
        rel = np.angle(np.exp(1j * (np.arctan2(off[:, 1], off[:, 0]) - base)))
        n = len(h.mates)
        angles = base + (np.arange(n) - (n - 1) / 2.0) * 2.0 * np.pi / n
        for i, a in zip(np.array(h.mates)[np.argsort(rel)], angles, strict=True):
            role(int(i), at + P.HUDDLE_RING * np.array([np.cos(a), np.sin(a)]), P.WALL_SPEED, None)

    def behind_ball(self) -> np.ndarray:
        """Unit vector from the ball to where the taker stands (``TAKER_BEHIND``)."""
        e = self.e
        r = e.restart
        if r.kind == "throw_in":
            return np.array([0.0, np.sign(r.spot[1]) or 1.0])
        if r.kind == "corner":
            return np.sign(r.spot) / np.sqrt(2.0)
        return e.to_uv(r.team, np.array([-1.0, 0.0]))

    def goal_side(self, team: int, xy: np.ndarray, metres: float) -> np.ndarray:
        """The point ``metres`` from ``xy`` towards the goal that ``team`` defends."""
        to_goal = self.e.to_uv(team, np.array([-GOAL_U, 0.0])) - xy
        return xy + to_goal / max(float(np.hypot(*to_goal)), 1e-6) * metres

    def targets(
        self, t: float
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """Target point, wanted speed (m/s), purpose code, calm flag (no run or ball role, see
        ``movement.step``) and anchored flag (on the ball, the receiver, the restart taker, in a
        wall, a set-piece attacker or the scorer of a goal: not pushed apart, see
        ``movement.push_apart``) for each player this frame. Team-mates' targets are already
        spread apart (``movement.spread_targets``), ``SEPARATION_DEAD`` apart while the ball is
        dead."""
        e = self.e
        mode = e.mode
        if self.declined:
            self.declined = {i: until for i, until in self.declined.items() if until > t}
        shape, holder = self.shape()
        tgt = movement.clip_to_pitch(shape + self.step_wander())
        frac = np.full(22, P.DEAD_SPEED if mode == "dead" else P.DRIFT_SPEED)
        purpose = np.full(22, NO_PURPOSE, dtype=np.int8)
        calm = np.ones(22, dtype=bool)
        anchored = np.zeros(22, dtype=bool)

        if mode != "dead" and holder is not None:
            self.start_shape_runs(t, shape, holder)
            # Attackers caught offside hurry back (their shape target is just onside).
            idx = e.members(holder)[1:]
            beyond = e.to_uv(holder, e.pos[idx])[:, 0] > self.onside_u(holder) + P.ONSIDE_MARGIN
            frac[idx[beyond]] = P.ONSIDE_SPEED
            calm[idx[beyond]] = False
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
            calm[i] = False

        def role(i: int, target: np.ndarray, speed: float, why: RunPurpose | None) -> None:
            tgt[i] = target
            frac[i] = speed
            purpose[i] = NO_PURPOSE if why is None else CODE[why]
            calm[i] = False

        if mode == "touch":
            c = e.touch.player
            anchored[c] = True
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
            press = self.goal_side(opp_team, e.pos[c], P.PRESS_GAP)
            cover = self.goal_side(opp_team, e.pos[c], P.COVER_DEPTH)
            for i in order[:n_press]:
                role(int(i), press, P.CHASE_SPEED, RunPurpose.CLOSE_DOWN)
            role(int(order[n_press]), cover, P.SHAPE_RUN_SPEED, RunPurpose.COVERING)
        elif mode == "flight":
            f = e.flight
            if f.result in ("intercepted", "clear"):
                role(f.to, f.end, P.CHASE_SPEED, RunPurpose.INTERCEPTION)
                anchored[f.to] = True
            elif f.to >= 0 and f.result in ("complete", "aerial", "offside"):
                chase = (
                    P.BEHIND_EFFORT
                    if self.receiver_purpose == RunPurpose.RUN_IN_BEHIND
                    else (P.CHASE_SPEED)
                )
                role(f.to, f.end, chase, self.receiver_purpose)
                anchored[f.to] = True
                defenders = e.members(1 - int(e.team_of[f.to]))[1:]
                d = np.hypot(*(e.pos[defenders] - f.end).T)
                j = int(np.argmin(d))
                closer = int(defenders[j])
                if f.challenger >= 0:
                    role(f.challenger, f.end, P.CHASE_SPEED, RunPurpose.INTERCEPTION)
                elif d[j] < P.CLOSE_DOWN_REACH:
                    spot = self.goal_side(int(e.team_of[closer]), f.end, P.PRESS_GAP)
                    role(closer, spot, P.CHASE_SPEED, RunPurpose.CLOSE_DOWN)
                keeper = int(e.members(1 - int(e.team_of[f.to]))[0])
                claim = self.keeper_claim(keeper, f.end)
                if claim is not None:
                    role(keeper, claim, P.CHASE_SPEED, None)
        elif mode == "loose":
            for k in (0, 1):
                idx = e.members(k)
                d = np.hypot(*(e.pos[idx] - e.loose_point).T)
                for i in idx[np.argsort(d)[:2]]:
                    role(int(i), e.loose_point, P.CHASE_SPEED, None)
        else:
            r = e.restart
            set_piece = e.set_piece()
            if set_piece:
                if self.plan_for is not r:
                    self.plan_for, self.plan = r, e.set_piece_plan(self.wander_rng)
                # Everyone jogs up, like the wall; attackers hold their spots, the markers settle
                # round them.
                for i, spot, holds in self.plan:
                    role(i, spot, P.WALL_SPEED, None)
                    anchored[i] = holds
            if r.kind == "free_kick":
                # The wall jogs into place; anchored, so the push-apart leaves its spacing alone.
                wall = self.wall(set_piece)
                for i, spot in wall:
                    role(i, spot, P.WALL_SPEED, None)
                    anchored[i] = True
                if wall:
                    self.keep_off_wall(tgt, [spot for _, spot in wall])
            if r.huddle is not None and t < r.huddle.t_end:
                self.huddle(r.huddle, t, role, anchored)
            role(r.taker, r.spot + self.behind_ball() * P.TAKER_BEHIND, 0.7 * P.CHASE_SPEED, None)
            anchored[r.taker] = True
        keep = P.SEPARATION_DEAD if mode == "dead" else P.SEPARATION_TEAM
        tgt = movement.spread_targets(tgt, e.team_of, anchored, keep)
        if mode == "dead":
            self.keep_distance(tgt)  # last, so that spreading cannot undo it
        effort = self.effort
        if self.tempo is not None and mode != "dead":
            effort = effort * self.tempo  # in play only: the set-piece jog stays below HI_SPEED
        frac = np.where(calm, frac, np.minimum(frac * effort, 1.0))
        if e.physiology is not None:
            frac = np.where(calm, frac, frac * e.physiology.speed_factor())
        return tgt, frac * e.s0, purpose, calm, anchored
