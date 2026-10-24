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
     A recovery run goes up to full effort only when there is danger (``DANGER_U``). On the
     opponents' counter-attack, or caught upfield of the ball, defenders drop from a smaller gap
     (``COUNTER_DROP_*``); back up to a line that is not moving, they jog.
   - *Triggered runs* start when a team-mate gets the ball or plays a pass: coming short to
     receive, exploiting space, midfield support, overlaps, breaking into the box, runs in
     behind, and, in a positive transition, support runs and forwards breaking towards goal.
     A defender goes with a runner in behind or into space towards goal, goal-side of him,
     while the run is still on (``track``). Out of possession, a forward or central midfielder
     may close down a new carrier.

3. **Roles on and around the ball**, set fresh every frame: the carrier (run with ball), the
   receiver (move to receive, or a run in behind onto a through ball, or into the box for a
   cross), the nearest defenders closing down the carrier or the receiver, the cover defender,
   the interceptor, the goalkeeper coming for a ball near goal, loose-ball chasers, and restart
   takers. While the ball is dead: opponents keep the legal distance, set pieces (a corner, or a
   free kick near goal) send six attackers and their markers forward, a free kick in range gets
   a wall, and after a goal the scorer's team-mates gather round them.

Each position's run and role speeds are scaled by its work rate (``POSITION_EFFORT``), and in
play by the match tempo (``TEMPO_SD``), which both teams share. A run back the way a player has
just sprinted waits for him to turn (``TURN_S``).

Runs are explicit decisions so that the fatigue model (``physiology.py``) can veto them: a tired
player may skip a hard run, and the runs they make are shorter (``start``); their runs and ball
roles are slower (``targets``). All the chances, distances and speeds are in ``params.py``; the
inline distances (where each triggered run aims) are our assumption.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

from runningbattery.schema import Position, RunPurpose
from runningbattery.sim import movement
from runningbattery.sim import params as P

if TYPE_CHECKING:
    from runningbattery.sim.match import MatchEngine

PURPOSES = list(RunPurpose)
CODE = {purpose: i for i, purpose in enumerate(PURPOSES)}
NO_PURPOSE = -1
GOAL_U = P.HALF_LENGTH
BACKS = (Position.CB, Position.FB, Position.DM)
FORWARDS = (Position.AM, Position.WM, Position.CF)
MIDFIELD = (Position.DM, Position.CM, Position.AM, Position.WM)
# Runs that defenders go with (``track``): in behind, and into space towards goal.
TRACKED = (RunPurpose.RUN_IN_BEHIND, RunPurpose.MOVE_TO_RECEIVE)


@dataclass
class Run:
    purpose: RunPurpose
    t_end: float
    speed: float  # wanted speed as a share of S0
    target: np.ndarray | None = None  # fixed pitch point
    offset_uv: np.ndarray | None = None  # or: this offset from the ball, in the team's frame
    shape: bool = False  # or: the player's shape target; ends once the gap has closed
    onside: bool = False  # keep the target level with the offside line
    follow: int = -1  # or: goal-side of this runner, while ``Roles.tracking`` holds
    follow_pass: int = -1  # the pass (event index) he is running for; -1: a run with the ball


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
        # When each player was last above HI_SPEED, and which way (``turning``).
        self.fast_t = np.full(22, -np.inf)
        self.fast_dir = np.zeros((22, 2))

    def clear(self) -> None:
        self.runs.clear()
        self.declined.clear()

    def start(self, i: int, run: Run, t: float, toward: np.ndarray | None = None) -> None:
        """Every run decision goes through here. With fatigue on, a hard run (wanted speed above
        ``HARD_RUN_SPEED``) is skipped with chance 1 − ``Physiology.run_choice``; the player
        then keeps to their calm movement (a tired player jogs back instead of sprinting) and is
        not asked again until the run's planned end, or for a shape run ``SHAPE_DECLINE_S``.
        Decisions on runs wanted above ``HI_SPEED`` are kept, with a forecast of whether the run
        would be a high-intensity run (``hi_forecast``); the skipped ones go to ``truth.json``.
        A run that is made lasts ``Physiology.shorten`` of its planned time. ``toward``: the
        gap to the target (m, x/y) for a shape run, whose target is not in ``run``."""
        body = self.e.physiology
        if body is not None:
            rate = self.effort[i] * (1.0 if self.tempo is None else self.tempo)
            if self.e.story_press(int(self.e.team_of[i]), t):
                rate *= self.e.story.press_effort
            want = min(run.speed * rate, 1.0) * self.e.s0[i]
            if want > P.HARD_RUN_SPEED:
                made = body.makes_run(i, run.speed >= P.DECISIVE_EFFORT)
                if want > P.HI_SPEED:
                    hi = self.hi_forecast(i, run, t, want, toward)
                    body.decide(i, t, run.t_end, run.purpose, made, hi)
                if not made:
                    self.declined[i] = (
                        min(run.t_end, t + P.SHAPE_DECLINE_S) if run.shape else run.t_end
                    )
                    return
                run.t_end = t + (run.t_end - t) * body.shorten(i)
        self.runs[i] = run

    def turning(self, i: int, way: np.ndarray, t: float) -> bool:
        """He was above HI_SPEED within ``TURN_S`` going the other way (more than 90° from
        ``way``): he has to turn first, so until then his run goes no faster than SHAPE_RUN_MIN
        (``targets``). Real players rarely sprint straight back the way they came (decision
        41)."""
        return t - self.fast_t[i] < P.TURN_S and float(self.fast_dir[i] @ way) < 0.0

    def hi_forecast(
        self, i: int, run: Run, t: float, want: float, toward: np.ndarray | None
    ) -> bool:
        """Whether the run, made fresh, would be a high-intensity run: ``forecast_hi_run`` with
        the target where it is now and the player's speed towards it (a run with no target
        yet: open space, at the player's speed)."""
        e = self.e
        if toward is None and run.target is not None:
            toward = np.asarray(run.target) - e.pos[i]
        elif toward is None and run.offset_uv is not None:
            toward = e.ball_xy[:2] + e.to_uv(int(e.team_of[i]), run.offset_uv) - e.pos[i]
        if toward is None:
            gap, v0 = np.inf, float(np.hypot(*e.vel[i]))
        else:
            gap = float(np.hypot(*toward))
            v0 = max(float(e.vel[i] @ toward) / gap, 0.0) if gap > 1e-6 else 0.0
        body = e.physiology
        return movement.forecast_hi_run(
            gap,
            want,
            v0,
            float(e.a0[i] * body.accel_mult[i]),
            float(e.s0[i] * body.speed_mult[i]),
            run.t_end - t,
            P.SHAPE_RUN_END if run.shape else 0.0,
        )

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
                    target[0] = min(target[0], GOAL_U - 8.0, self.behind_cap(team))
                    t_end = min(e.transition[1], t + rng.uniform(*P.SPRINT_RUN_S))
                    run = Run(RunPurpose.RUN_IN_BEHIND, t_end, P.BEHIND_EFFORT)
                    run.target = e.inside(e.to_uv(team, target))
                    self.start(i, run, t)
                    self.track(t, i, on_pass=False)

    def on_touch(self, carrier: int, t: float) -> None:
        """A team-mate has the ball: someone may come short, overlap, or break into the box."""
        e = self.e
        rng = e.rng
        self.runs.pop(carrier, None)
        team = int(e.team_of[carrier])
        idx = [int(i) for i in e.members(team) if i != carrier]
        c_xy = e.pos[carrier]
        c_u, c_v = e.to_uv(team, c_xy)
        # Close-down runs follow the ball, so they were aimed at the last carrier: they end.
        for i, run in list(self.runs.items()):
            if run.purpose == RunPurpose.CLOSE_DOWN and int(e.team_of[i]) != team:
                del self.runs[i]
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
            self.track(t, i, on_pass=False)

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
        if e.story_press(team, t):
            chance = min(chance * e.story.press_run_boost, 1.0)
        near = [int(i) for i in e.members(team) if who[i] and self.free(int(i))]
        if not near or e.rng.random() >= chance:
            return
        mates = e.members(team)[1:]
        if np.hypot(*(e.pos[mates] - e.pos[carrier]).T).min() < P.PRESS_COVERED:
            return  # a team-mate is already on the carrier
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
            self.track(t, receiver)
        elif cross:
            self.receiver_purpose = RunPurpose.BREAK_INTO_BOX
        else:
            self.receiver_purpose = RunPurpose.MOVE_TO_RECEIVE
        self.runs.pop(receiver, None)
        if not open_play:
            return
        team = int(e.team_of[passer])
        if e.to_uv(team, end)[0] - e.to_uv(team, e.pos[passer])[0] < P.BEHIND_PASS_FORWARD:
            return  # a square or backward pass: the receiver cannot play a forward in behind
        line = e.offside_line(team, e.pos[passer])
        cap = self.behind_cap(team)
        for i in e.members(team):
            i = int(i)
            if i in (passer, receiver) or not self.is_forward[i] or not self.free(i):
                continue
            i_u, i_v = e.to_uv(team, e.pos[i])
            if line - P.THROUGH_BALL_NEAR_LINE < i_u <= line and rng.random() < P.BEHIND_CHANCE:
                depth = rng.uniform(*P.BEHIND_DEPTH)
                if min(line + depth, cap) <= i_u:
                    continue  # the keeper is out at the line: no space in behind
                target_uv = np.array([min(line + depth, GOAL_U - 6.0, cap), 0.8 * i_v])
                t_end = t + rng.uniform(*P.SPRINT_RUN_S)
                run = Run(RunPurpose.RUN_IN_BEHIND, t_end, P.BEHIND_EFFORT)
                run.target = e.inside(e.to_uv(team, target_uv))
                self.start(i, run, t)
                self.track(t, i)

    def behind_cap(self, team: int) -> float:
        """How deep (u, in ``team``'s frame) a run in behind may aim: ``BEHIND_KEEPER_GAP``
        short of the opponents' goalkeeper, and no nearer goal than ``BEHIND_GOAL_GAP``."""
        keeper = int(self.e.members(1 - team)[0])
        u = float(self.e.to_uv(team, self.e.pos[keeper])[0]) - P.BEHIND_KEEPER_GAP
        return min(u, GOAL_U - P.BEHIND_GOAL_GAP)

    def track(self, t: float, runner: int, on_pass: bool = True) -> None:
        """The defenders (CB, FB) nearest a runner (in behind, or into space towards goal) go
        with him, goal-side of him (a recovery run), while ``tracking`` holds: for a pass
        (``on_pass``; called before it is logged, so it is the next event), or for a run while
        his team has the ball. A defender already following him keeps the job."""
        e = self.e
        team = 1 - int(e.team_of[runner])
        on = len(e.events) if on_pass else -1
        for run in self.runs.values():
            if run.follow == runner:
                run.follow_pass = on
                run.t_end = max(run.t_end, t + P.SPRINT_RUN_S[0])
                return
        idx = [int(i) for i in e.members(team) if self.is_defender[i] and self.free(int(i))]
        idx.sort(key=lambda i: float(np.hypot(*(e.pos[i] - e.pos[runner]))))
        for i in idx[: P.TRACKERS]:
            run = Run(RunPurpose.RECOVERY_RUN, t + e.rng.uniform(*P.SPRINT_RUN_S), P.TRACK_EFFORT)
            run.target = e.inside(self.goal_side(team, e.pos[runner], P.TRACK_GOAL_SIDE))
            run.follow, run.follow_pass = runner, on
            self.start(i, run, t)

    def tracking(self, run: Run) -> bool:
        """A tracker keeps on while his runner has the ball, and while the pass is in flight and
        his runner is still running for it (or it is going to him); for a run while his team has
        the ball (no pass), while a team-mate of the runner carries it and the run is still on
        (``TRACKED``).
        Not once the pass reached someone else, or the ball is loose or won (decision 41)."""
        e = self.e
        r = run.follow
        other = self.runs.get(r)
        running = other is not None and other.purpose in TRACKED
        if e.mode == "touch":
            c = e.touch.player
            mate = run.follow_pass < 0 and e.team_of[c] == e.team_of[r]
            return c == r or (mate and running)
        if e.mode != "flight" or e.flight.event != run.follow_pass:
            return False
        if e.flight.to == r and e.flight.result in ("complete", "aerial", "offside"):
            return True
        return running

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
        # How far each team's outfield players are below their shape targets (up the pitch, in
        # the team's frame): the line stepping up, when it is most of them (decision 41).
        line_u = [float(np.median(e.to_uv(k, gap_xy[e.members(k)[1:]])[:, 0])) for k in (0, 1)]
        # On the opponents' counter-attack, or caught upfield of the ball, the defenders drop at
        # once (COUNTER_DROP_GAP).
        start_gap = np.full(22, P.SHAPE_RUN_GAP)
        for k in (0, 1):
            if k == holder:
                continue
            idx = e.members(k)
            counter = e.transition is not None and e.transition[0] != k
            beaten = e.to_uv(k, e.pos[idx])[:, 0] > e.to_uv(k, e.ball_xy[:2])[0]
            dropping = self.is_defender[idx] & (counter | beaten)
            start_gap[idx[dropping]] = P.COUNTER_DROP_GAP
        for i in np.flatnonzero(gap > start_gap):
            i = int(i)
            if not self.free(i):
                continue
            team = int(e.team_of[i])
            gap_u = e.to_uv(team, gap_xy[i])[0]
            urgency = np.clip(
                (gap[i] - P.SHAPE_RUN_GAP) / (P.SHAPE_RUN_FULL - P.SHAPE_RUN_GAP), 0, 1
            )
            speed = P.SHAPE_RUN_MIN + (P.SHAPE_RUN_SPEED - P.SHAPE_RUN_MIN) * float(urgency)
            if start_gap[i] < P.SHAPE_RUN_GAP:
                speed = max(speed, P.COUNTER_DROP_SPEED)
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
                elif gap_u > 0.5 * gap[i] and gap_u - line_u[team] > P.SHAPE_RUN_GAP:
                    speed = min(speed, P.SHAPE_RUN_MIN)  # back up to a line that is not moving
            run = Run(purpose, t + P.SHAPE_RUN_MAX_S, speed, shape=True)
            self.start(i, run, t, gap_xy[i])

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
        spot = goal + gap / max(dist, 1e-6) * max(dist - 1.0, 0.5)
        spot[0] = min(spot[0], -GOAL_U + P.GK_MAX_OFF)
        return self.e.to_uv(team, spot)

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
        # Straight across: either way round, but the same way every frame (decision 41: the
        # sign flipped and a player walking off stood at the edge for a minute).
        turn = np.where(np.abs(turn) > np.pi - P.RESTART_ARC_STEP, P.RESTART_ARC_STEP, turn)
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

    def dead_pace(self, i: int, spot: np.ndarray, t: float) -> float:
        """Wanted speed (share of S0, before the work rate) of a set-piece job while the ball is
        dead: the pace that reaches ``spot`` once ``SET_PIECE_DUE`` of the dead time has gone,
        from a walk (``SET_PIECE_WALK``) up to the jog (``WALL_SPEED``, which ``targets`` also
        applies after the work rate)."""
        e = self.e
        r = e.restart
        left = max(r.t_dead + P.SET_PIECE_DUE * (r.t - r.t_dead) - t, 1.0)
        need = float(np.hypot(*(spot - e.pos[i]))) / left / (e.s0[i] * self.effort[i])
        return min(max(need, P.SET_PIECE_WALK), P.WALL_SPEED)

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
        sp = np.hypot(*e.vel.T)
        fast = sp > P.HI_SPEED
        self.fast_t[fast] = t
        self.fast_dir[fast] = e.vel[fast] / sp[fast, None]
        shape, holder = self.shape()
        tgt = movement.clip_to_pitch(shape + self.step_wander())
        frac = np.full(22, P.DEAD_SPEED if mode == "dead" else P.DRIFT_SPEED)
        purpose = np.full(22, NO_PURPOSE, dtype=np.int8)
        calm = np.ones(22, dtype=bool)
        anchored = np.zeros(22, dtype=bool)
        jog = np.zeros(22, dtype=bool)  # at most WALL_SPEED after the work rate (decision 42)

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
            elif run.follow >= 0:
                if not self.tracking(run):
                    del self.runs[i]
                    continue
                target = self.goal_side(team, e.pos[run.follow], P.TRACK_GOAL_SIDE)
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
            if self.turning(i, tgt[i] - e.pos[i], t):
                frac[i] = min(run.speed, P.SHAPE_RUN_MIN)
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
            pressers = [int(i) for i in idx if purpose[int(i)] == CODE[RunPurpose.CLOSE_DOWN]]
            if len(pressers) > 1:
                to_goal = e.to_uv(opp_team, np.array([-GOAL_U, 0.0])) - e.pos[c]
                unit = to_goal / max(float(np.hypot(*to_goal)), 1e-6)
                across = np.array([-unit[1], unit[0]])
                pressers.sort(key=lambda j: float((e.pos[j] - e.pos[c]) @ across))
                for k_p, j in enumerate(pressers):
                    side = (k_p - (len(pressers) - 1) / 2.0) * 1.6
                    tgt[j] = movement.clip_to_pitch(press + side * across)
            ch = e.touch.challenger
            if ch >= 0:  # going in for the ball (match.update_touch): through it, where it will
                # be in ARRIVE_TAU, plus a stride, so that he does not ease off as he gets near
                ball = e.ball_xy[:2] + e.vel[c] * P.ARRIVE_TAU
                way = ball - e.pos[ch]
                aim = ball + way / max(float(np.hypot(*way)), 1e-6) * 1.5
                role(ch, movement.clip_to_pitch(aim), P.DUEL_APPROACH, RunPurpose.CLOSE_DOWN)
        elif mode == "flight":
            f = e.flight
            if f.result in ("intercepted", "clear"):
                role(f.to, f.end, P.CHASE_SPEED, RunPurpose.INTERCEPTION)
                anchored[f.to] = True
            elif f.result == "won":  # a tackle won: he steps to the ball (match.take_ball)
                role(f.to, f.end, P.CHASE_SPEED, None)
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
                if f.challenger >= 0:  # the pace that gets him under it in time (decision 41)
                    ch = f.challenger
                    way = f.end - e.pos[ch]
                    aim = e.pos[ch] + way * max(P.ARRIVE_TAU / max(f.t1 - t, P.DT), 1.0)
                    role(ch, movement.clip_to_pitch(aim), P.CHASE_SPEED, RunPurpose.INTERCEPTION)
                elif d[j] < P.CLOSE_DOWN_REACH:
                    spot = self.goal_side(int(e.team_of[closer]), f.end, P.PRESS_GAP)
                    role(closer, spot, P.CHASE_SPEED, RunPurpose.CLOSE_DOWN)
                keeper = int(e.members(1 - int(e.team_of[f.to]))[0])
                claim = self.keeper_claim(keeper, f.end)
                if claim is not None:
                    role(keeper, claim, P.CHASE_SPEED, None)
        elif mode == "loose":
            for k in (0, 1):
                can_gk = float(e.to_uv(k, e.loose_point)[0]) <= -GOAL_U + P.GK_MAX_OFF
                idx = e.members(k) if can_gk else e.members(k)[1:]
                d = np.hypot(*(e.pos[idx] - e.loose_point).T)
                for i in idx[np.argsort(d)[: P.LOOSE_CHASERS]]:
                    role(int(i), e.loose_point, P.CHASE_SPEED, None)
        else:
            r = e.restart
            set_piece = e.set_piece()
            if set_piece:
                if self.plan_for is not r:
                    self.plan_for, self.plan = r, e.set_piece_plan(self.wander_rng)
                # Everyone goes up, like the wall; attackers hold their spots, the markers settle
                # round them.
                for i, spot, holds in self.plan:
                    role(i, spot, self.dead_pace(i, spot, t), None)
                    anchored[i] = holds
            if r.kind == "free_kick":
                # The wall forms; anchored, so the push-apart leaves its spacing alone.
                wall = self.wall(set_piece)
                for i, spot in wall:
                    role(i, spot, self.dead_pace(i, spot, t), None)
                    anchored[i] = True
                if wall:
                    self.keep_off_wall(tgt, [spot for _, spot in wall])
            if r.huddle is not None and t < r.huddle.t_end:
                self.huddle(r.huddle, t, role, anchored)
            behind = 0.3 if r.kind == "throw_in" else P.TAKER_BEHIND
            spot = r.spot + self.behind_ball() * behind
            role(r.taker, spot, self.dead_pace(r.taker, spot, t), None)
            anchored[r.taker] = True
            # Substitutions (match.substitute_due): the replaced player walks off.
            for i, (_, exit_xy, _) in e.leaving.items():
                role(i, exit_xy, P.SUB_OFF_SPEED, None)
                anchored[i] = True
        # The substitute jogs to his place in the shape, the ball dead or not (at most SUB_MAX_S),
        # unless the ball comes to him.
        for i, due in list(e.entering.items()):
            if np.hypot(*(shape[i] - e.pos[i])) < P.SHAPE_RUN_GAP or t >= due + P.SUB_MAX_S:
                del e.entering[i]
            elif not anchored[i]:
                role(i, shape[i], P.WALL_SPEED, None)
                jog[i] = True
        for k in (0, 1):
            gk = int(e.members(k)[0])
            if mode != "dead" or e.restart.taker != gk:
                gk_uv = e.to_uv(k, tgt[gk])
                gk_uv[0] = min(gk_uv[0], -GOAL_U + P.GK_MAX_OFF)
                tgt[gk] = e.to_uv(k, gk_uv)
                # At his limit he stops there, not with a calm drift's slow braking (decision 41:
                # moving out at 2.4 m/s he drifted 2.5 m past it).
                if e.to_uv(k, e.pos[gk])[0] > -GOAL_U + P.GK_MAX_OFF - P.GK_BRAKE_M:
                    calm[gk] = False
        keep = P.SEPARATION_DEAD if mode == "dead" else P.SEPARATION_TEAM
        tgt = movement.spread_targets(tgt, e.team_of, anchored, keep)
        if mode == "dead":
            self.keep_distance(tgt)  # last, so that spreading cannot undo it
            anchored = anchored & (np.hypot(*(tgt - e.pos).T) < 1.2)
        effort = self.effort
        if self.tempo is not None and mode != "dead":
            effort = effort * self.tempo  # in play only: the set-piece jog stays below HI_SPEED
        if e.story is not None and mode != "dead":
            press = e.story.press_team
            if e.story_press(press, t):
                effort = np.where(e.team_of == press, effort * e.story.press_effort, effort)
        frac = np.where(calm, frac, np.minimum(frac * effort, 1.0))
        if mode == "dead":  # every job while the ball is dead is a walk or a jog
            jog |= ~calm
        frac = np.where(jog, np.minimum(frac, P.WALL_SPEED), frac)
        if e.physiology is not None:
            frac = np.where(calm, frac, frac * e.physiology.speed_factor())
        return tgt, frac * e.s0, purpose, calm, anchored
