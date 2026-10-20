"""Match flow for generator v0: one state machine stepped at 10 Hz, together with movement.

The ball is always in one of four modes:

- ``dead``: out of play, waiting for a restart (kick-off, throw-in, goal kick, corner, free kick).
- ``touch``: a player has it. The touch ends in a pass, a shot, or a ground duel that loses it.
- ``flight``: a pass, shot or clearance in the air or along the ground. Its result (received,
  intercepted, aerial duel, out of play, loose, goal, saved, wide, blocked) is drawn at the kick.
- ``loose``: nobody controls it; the first player to reach it logs a ball recovery.

Each frame the flow is updated first (and may log events), then the frame is recorded, then
every player takes one movement step towards a target from the team shape, their runs and their
role (``roles.py``). The purpose behind each player's movement is recorded too, so that every
high-intensity run can be labelled afterwards (``runs.py``). With fatigue on, each player's
hidden physiology (``physiology.py``) is updated from their speed after every step: it lowers
their capacity (S0, A0), and ``roles.py`` reads it to skip, shorten and slow runs; carries are
slower too. A shared match tempo, if given, scales both teams' work rate in play.

Substitutions (``rosters.plan_substitutions``) are made at the first stoppage from their planned
time, half-time ones at the second-half kick-off [IFAB2025, Law 3]: the substitute takes over the
engine slot (its index 0–21 stays the same, its player id changes), fresh, with their own hidden
values (``Physiology.substitute``). ``ids`` is the player in each slot now; events keep the ids
of the moment, and ``sub_log`` says who was where when.

Conventions (our choices, needed by the estimator and the agents later):

- ``possession_id`` goes up by one whenever the team in control changes, and at each kick-off
  that starts a period.
- Phases come from the viewpoint of the event's team (``Phase`` in schema.py). Interceptions,
  recoveries and receptions are labelled as the first moment of the new possession; duels,
  tackles, pressures and fouls from the defending side.
- A transition is the first seconds after an open-play turnover [Bortnik2022]; only a share of
  turnovers start one (``params.TRANSITION_CHANCE``).
- Offside is called on the receiver when the pass arrives, and gives an indirect free kick
  [IFAB2025, Law 11]. No penalties in v0: fouls in the box are moved to its edge (our
  assumption).

Tuned values live in ``params.py`` with their sources. The few small numbers written inline here
(shot, clearance and loose-ball speeds, pass-success nudges, carry and touch limits) are our
assumption.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from runningbattery.schema import BodyPart, EventType, Outcome, PassHeight, Phase, Position
from runningbattery.sim import movement
from runningbattery.sim import params as P
from runningbattery.sim.physiology import Physiology
from runningbattery.sim.roles import Roles
from runningbattery.sim.rosters import SimTeam, SubPlan
from runningbattery.sim.story import Story

GRAVITY = 9.81
GOAL_U = P.HALF_LENGTH
NO_OFFSIDE = ("throw_in", "goal_kick", "corner")  # restarts with no offside [IFAB2025, Law 11]


def snap(t: float) -> float:
    """Round a time up to the 10 Hz frame grid."""
    return round(math.ceil(t * P.FRAME_RATE_HZ - 1e-6) / P.FRAME_RATE_HZ, 1)


@dataclass
class Flight:
    start: np.ndarray
    end: np.ndarray
    t0: float
    t1: float
    peak_z: float
    result: str
    by: int  # last player to touch the ball
    to: int = -1  # player who gets it at t1 (receiver, interceptor, keeper, blocker)
    challenger: int = -1  # opponent in an aerial duel
    receiver_wins: bool = True


@dataclass
class Touch:
    player: int
    t0: float
    t_release: float
    start: np.ndarray
    carry_to: np.ndarray
    carry_speed: float
    duel_at: float | None
    header: bool


@dataclass
class Huddle:
    scorer: int
    spot: np.ndarray  # where the scorer jogs to
    mates: list[int]  # team-mates who gather round
    t_end: float  # moved earlier once they have all arrived (HUDDLE_HOLD_S)
    formed: bool = False


@dataclass
class Restart:
    kind: str
    team: int
    spot: np.ndarray
    t: float  # earliest time it can be taken
    taker: int
    ball_from: np.ndarray
    t_dead: float
    huddle: Huddle | None = None  # after a goal


@dataclass
class PeriodFrames:
    period: int
    pos: np.ndarray  # (n, 22, 2)
    ball: np.ndarray  # (n, 3)
    alive: np.ndarray  # (n,) bool
    possession: np.ndarray  # (n,) int8 team index, -1 when contested
    purpose: np.ndarray  # (n, 22) int8 code of the movement's purpose (roles.PURPOSES), -1 none
    subs: list[tuple[int, int, str]] = field(default_factory=list)  # (frame, slot, id coming on)


class MatchEngine:
    def __init__(
        self,
        rng: np.random.Generator,
        teams: list[SimTeam],
        physiology: Physiology | None = None,
        tempo: float | None = None,
        pre_fatigue: bool = False,
        subs: list[SubPlan] | None = None,
        story: Story | None = None,
    ):
        """``physiology`` None is fatigue off; ``tempo`` None is no shared tempo.
        ``pre_fatigue`` uses the fatigue-off calibration (``params.PRE_FATIGUE``); with both off
        and no ``subs`` too, the engine is the generator as it was before fatigue and tempo
        existed. ``story``: the demo's story controls (``sim.story``), None for natural matches."""
        self.rng = rng
        self.story = story
        self.teams = teams
        self.physiology = physiology
        self.tempo = tempo
        self.pre_fatigue = pre_fatigue
        players = [p for team in teams for p in team.players]
        self.ids = [p.id for p in players]
        self.positions = [p.position for p in players]
        self.team_of = np.repeat([0, 1], 11)
        self.a0 = np.array([p.params.a0 for p in players])
        self.s0 = np.array([p.params.s0 for p in players])
        self.slots = [np.array([p.slot for p in team.players]) for team in teams]
        self.hold = [
            np.array([P.OUT_OF_POSSESSION_HOLD.get(p.position, 0.0) for p in team.players])
            for team in teams
        ]
        self.events: list[dict] = []
        self.score = [0, 0]
        self.poss_id = 0
        self.transition_spans: list[float] = []  # realised length of each transition, s
        self.pending = sorted(subs or [], key=lambda s: (s.clock_s, s.slot))
        self.sub_log: list[tuple[int, float, int, str, str]] = []  # period, t, slot, off, on
        self.roles = Roles(self)

    # --- Geometry ----------------------------------------------------------------------------

    def members(self, team: int) -> np.ndarray:
        return np.arange(11) + 11 * team

    def to_uv(self, team: int, xy: np.ndarray) -> np.ndarray:
        """Pitch (x, y) to the team's attacking frame (u, v). The map is its own inverse."""
        return xy * self.dir[team]

    def nearest(self, team: int, point: np.ndarray, skip_gk: bool = False) -> tuple[int, float]:
        idx = self.members(team)
        if skip_gk:
            idx = idx[1:]
        d = np.hypot(*(self.pos[idx] - point).T)
        i = int(np.argmin(d))
        return int(idx[i]), float(d[i])

    def nearest_to_segment(self, team: int, a: np.ndarray, b: np.ndarray) -> tuple[int, float]:
        """Outfield player of ``team`` closest to segment a→b, and where along it (0–1)."""
        idx = self.members(team)[1:]
        ab = b - a
        s = np.clip(((self.pos[idx] - a) @ ab) / max(ab @ ab, 1e-9), 0.0, 1.0)
        d = np.hypot(*(a + s[:, None] * ab - self.pos[idx]).T)
        i = int(np.argmin(d))
        return int(idx[i]), float(s[i])

    def zone(self, team: int, xy: np.ndarray) -> int:
        """0, 1, 2 for the team's own, middle and attacking third."""
        u = self.to_uv(team, xy)[0]
        return 0 if u < -P.THIRD else (1 if u < P.THIRD else 2)

    def offside_line(self, team: int, ball: np.ndarray) -> float:
        """u in ``team``'s frame beyond which a team-mate is offside [IFAB2025, Law 11]."""
        opp_u = np.sort(self.to_uv(team, self.pos[self.members(1 - team)])[:, 0])
        return max(float(opp_u[-2]), float(self.to_uv(team, ball)[0]), 0.0)

    def inside(self, xy: np.ndarray, edge: float = 1.0) -> np.ndarray:
        return movement.clip_to_pitch(xy, edge)

    # --- Events ------------------------------------------------------------------------------

    def log(self, type_: EventType, t: float, player: int = -1, **fields) -> None:
        team = int(self.team_of[player]) if player >= 0 else fields.pop("team", None)
        restart = fields.pop("restart", False)
        phase = fields.pop("phase", None)
        ev = {
            "period": self.period,
            "t": round(t, 1),
            "type": type_,
            "player": player,
            "player_id": self.ids[player] if player >= 0 else None,
            "team": team,
            "score": tuple(self.score),
            "seq": len(self.events),
        }
        for key in ("start", "end"):
            if fields.get(key) is not None:
                fields[key] = self.event_point(fields[key])
        ev.update(fields)
        if isinstance(fields.get("related_player_id"), int | np.integer):
            ev["related_player_id"] = self.ids[fields["related_player_id"]]
        if team is not None:
            ev["possession_id"] = self.poss_id
            where = fields.get("start", (self.ball_xy[0], self.ball_xy[1]))
            ev["phase"] = phase or self.phase(team, np.array(where), restart)
        self.events.append(ev)

    @staticmethod
    def event_point(xy) -> tuple[float, float]:
        x = float(np.clip(xy[0], -P.HALF_LENGTH - 7, P.HALF_LENGTH + 7))
        y = float(np.clip(xy[1], -P.HALF_WIDTH - 5, P.HALF_WIDTH + 5))
        return round(x, 2) + 0.0, round(y, 2) + 0.0

    def phase(self, team: int, where: np.ndarray, restart: bool) -> Phase:
        if restart:
            return Phase.SET_PIECE
        if self.last_team == team:
            if self.transition and self.transition[0] == team:
                return Phase.POSITIVE_TRANSITION
            u = self.to_uv(team, where)[0]
            if u < -P.THIRD:
                return Phase.BUILD_UP
            return Phase.PROGRESSION if u < P.THIRD else Phase.FINAL_THIRD
        if self.transition and self.transition[0] != team:
            return Phase.NEGATIVE_TRANSITION
        if self.press and self.press[0] == team:
            return Phase.HIGH_PRESS
        return Phase.DEFENSIVE_BLOCK

    # --- Possession --------------------------------------------------------------------------

    def gain_possession(self, team: int, t: float, open_play: bool, where: np.ndarray) -> None:
        self.poss_team = team
        if team == self.last_team:
            return
        turnover = self.last_team is not None and open_play
        self.last_team = team
        self.poss_id += 1
        self.end_transition(t)
        self.press = None
        rng = self.rng
        if turnover and rng.random() < P.TRANSITION_CHANCE:
            mean, sd, lo, hi = P.TRANSITION_S
            self.transition = (team, t + float(np.clip(rng.normal(mean, sd), lo, hi)))
            self.transition_start = t
        elif self.to_uv(team, where)[0] < -P.THIRD:
            if rng.random() < self.press_chance(1 - team, t):
                self.press = (1 - team, t + P.PRESS_MAX_S)
        self.roles.on_possession_change(team, t)

    def clock(self, t: float) -> float:
        return t + (45.0 * 60.0 if self.period == 2 else 0.0)

    def story_press(self, team: int, t: float) -> bool:
        """The team is pressing high because the story says so (``sim.story``)."""
        return self.story is not None and self.story.pressing(team, self.clock(t))

    def press_chance(self, team: int, t: float) -> float:
        if self.story_press(team, t):
            return self.story.press_chance
        return self.teams[team].press_chance

    def end_transition(self, t: float) -> None:
        """A transition ends when its time is up, the ball changes hands, or play stops."""
        if self.transition is not None:
            self.transition_spans.append(t - self.transition_start)
            self.transition = None

    def lose_control(self) -> None:
        """The ball is loose or contested: tracking shows no team in possession."""
        self.poss_team = None

    # --- Touches -----------------------------------------------------------------------------

    def start_touch(self, player: int, t: float, header: bool = False) -> None:
        rng = self.rng
        team = int(self.team_of[player])
        is_gk = self.positions[player] == Position.GK
        if header:
            hold = rng.uniform(0.2, 0.6)
        else:
            median = P.GK_TOUCH_MEDIAN if is_gk else P.TOUCH_MEDIAN
            hold = float(np.clip(rng.lognormal(math.log(median), P.TOUCH_SIGMA), 0.3, 8.0))
        in_transition = self.transition is not None and self.transition[0] == team
        if is_gk:
            speed = 0.8
        elif in_transition:
            speed = rng.uniform(*P.CARRY_SPEED_TRANSITION)
        else:
            speed = rng.uniform(*P.CARRY_SPEED)
        if not is_gk:
            speed = max(speed, P.CARRY_MOMENTUM * float(np.hypot(*self.vel[player])))
            if self.physiology is not None:
                speed *= self.physiology.carry(player)  # slower, so shorter [Fang2024, Fig. 1]
        start = self.pos[player].copy()
        # Carry towards the opponent's goal, with a spread of angles and a pull to the middle.
        u, v = self.to_uv(team, start)
        angle = rng.normal(-0.01 * v, P.CARRY_ANGLE_SD[self.zone(team, start)])
        heading = self.to_uv(team, np.array([math.cos(angle), math.sin(angle)]))
        carry_to = self.inside(start + heading * speed * hold, edge=1.5)
        duel_at = None
        if not is_gk and rng.random() < P.DUEL_PER_TOUCH:
            duel_at = t + rng.uniform(0.3, 0.9) * hold
        self.touch = Touch(player, t, snap(t + hold), start, carry_to, speed, duel_at, header)
        self.mode = "touch"
        opp, dist = self.nearest(1 - team, start)
        if dist < P.PRESSURE_RADIUS:
            self.log(
                EventType.PRESSURE,
                t,
                opp,
                related_player_id=player,
                start=self.pos[opp],
                end_t=self.touch.t_release,
            )
        self.roles.on_touch(player, t)

    def end_touch(self, t: float) -> None:
        tc = self.touch
        end = self.pos[tc.player]
        if np.hypot(*(end - tc.start)) >= P.MIN_CARRY_LENGTH and t > tc.t0:
            self.log(EventType.CARRY, tc.t0, tc.player, start=tc.start, end=end, end_t=t)

    def update_touch(self, t: float) -> None:
        tc = self.touch
        if tc.duel_at is not None and t >= tc.duel_at:
            opp, dist = self.nearest(1 - int(self.team_of[tc.player]), self.pos[tc.player])
            if dist <= P.DUEL_REACH:
                self.ground_duel(t, opp)
                return
        if t >= tc.t_release:
            self.release(t)

    def release(self, t: float) -> None:
        tc = self.touch
        self.end_touch(t)
        c = tc.player
        team = int(self.team_of[c])
        u, v = self.to_uv(team, self.pos[c])
        d_goal = math.hypot(GOAL_U - u, v)
        if self.positions[c] != Position.GK and d_goal < P.SHOT_RANGE:
            rate = P.SHOT_RATE * math.exp(-d_goal / P.SHOT_RATE_SCALE)
            if self.rng.random() < rate:
                self.shoot(t, c, tc.header)
                return
        self.play_pass(t, c, self.pos[c].copy())

    def ground_duel(self, t: float, opp: int) -> None:
        rng = self.rng
        c = self.touch.player
        where = self.pos[c].copy()
        r = rng.random()
        duel = dict(related_player_id=c, start=where, subtype="ground", body_part=BodyPart.FOOT)
        if r < P.FOUL_PER_DUEL:
            self.log(EventType.DUEL, t, opp, outcome=Outcome.FAIL, **duel)
            self.end_touch(t)
            self.log(EventType.FOUL, t, opp, related_player_id=c, start=where)
            if rng.random() < P.CARD_PER_FOUL:
                self.log(EventType.CARD, t, opp, subtype="yellow")
            self.free_kick(t, int(self.team_of[c]), where)
        elif r < P.FOUL_PER_DUEL + (1 - P.FOUL_PER_DUEL) * P.DUEL_CHALLENGER_WINS:
            self.log(EventType.DUEL, t, opp, outcome=Outcome.SUCCESS, **duel)
            self.log(EventType.TACKLE, t, opp, outcome=Outcome.SUCCESS, start=where)
            self.end_touch(t)
            self.log(EventType.BALL_LOSS, t, c, subtype="tackled", start=where)
            if rng.random() < P.DUEL_TACKLER_KEEPS:
                self.gain_possession(int(self.team_of[opp]), t, True, where)
                self.start_touch(opp, t)
            else:
                self.kick_loose(t, where, rng.uniform(3.0, 8.0), opp)
        else:
            self.log(EventType.DUEL, t, opp, outcome=Outcome.FAIL, **duel)
            self.touch.duel_at = None
            self.touch.t_release = snap(max(self.touch.t_release, t) + 0.5)

    # --- Passes ------------------------------------------------------------------------------

    def choose_receiver(self, c: int, origin: np.ndarray, restart: str | None) -> int:
        rng = self.rng
        team = int(self.team_of[c])
        mates = np.array([i for i in self.members(team) if i != c])
        gap = self.pos[mates] - origin
        length = np.hypot(*gap.T)
        gain_u = self.to_uv(team, self.pos[mates])[:, 0] - self.to_uv(team, origin)[0]
        pref, sd = P.PASS_LENGTH_PREF, P.PASS_LENGTH_SD
        in_transition = self.transition is not None and self.transition[0] == team
        zone = self.zone(team, origin)
        fwd = P.PASS_FORWARD_GAIN_TRANSITION if in_transition else P.PASS_FORWARD_GAIN[zone]
        if restart == "throw_in":
            pref, sd, fwd = 12.0, 6.0, 0.05
        elif restart == "kick_off":
            pref, sd, fwd = 10.0, 5.0, -0.3
        elif restart == "goal_kick" and rng.random() < 0.5:
            pref, sd = 45.0, 10.0  # long goal kick; otherwise the usual short options
        weight = np.exp(-((length - pref) ** 2) / (2 * sd**2)) * np.exp(fwd * gain_u)
        opp = self.pos[self.members(1 - team)]
        free = np.min(np.hypot(*(self.pos[mates][:, None, :] - opp[None]).transpose(2, 0, 1)), 1)
        weight *= np.clip(free / 5.0, 0.15, 1.5)
        story = self.story
        if story is not None and in_transition and team != story.exposed_slot // 11:
            near = np.hypot(*(self.pos[mates] - self.pos[story.exposed_slot]).T)
            weight = np.where(near < story.counter_reach, weight * story.counter_bias, weight)
        weight[[self.positions[i] == Position.GK for i in mates]] *= 0.2
        mates_uv = self.to_uv(team, self.pos[mates])
        in_box = (mates_uv[:, 0] > GOAL_U - P.BOX_DEPTH - 4) & (
            np.abs(mates_uv[:, 1]) < P.BOX_HALF_WIDTH
        )
        if restart in ("corner", "free_kick_box") and in_box.any():
            weight = np.where(in_box, weight + 1e-3, 0.0)
        elif restart is None and zone == 2:
            weight = np.where(in_box, weight * P.BOX_RECEIVER_WEIGHT, weight)
        if restart not in NO_OFFSIDE:
            beyond = mates_uv[:, 0] - self.offside_line(team, origin)
            seen = P.OFFSIDE_PASS_WEIGHT * np.exp(-np.maximum(beyond, 0.0) / P.OFFSIDE_SEEN)
            weight = np.where(beyond > 0, weight * seen, weight)
        weight = weight / weight.sum()
        return int(mates[rng.choice(len(mates), p=weight)])

    def play_pass(self, t: float, c: int, origin: np.ndarray, restart: str | None = None) -> None:
        rng = self.rng
        team = int(self.team_of[c])
        r = self.choose_receiver(c, origin, restart)
        o_uv = self.to_uv(team, origin)
        r_uv = self.to_uv(team, self.pos[r])
        guess = max(np.hypot(*(self.pos[r] - origin)), 3.0) / 14.0
        end = self.pos[r] + self.vel[r] * guess * 0.6 + rng.normal(0.0, 1.0, 2)
        line = self.offside_line(team, origin)
        offside = restart not in NO_OFFSIDE and r_uv[0] > line
        through = (
            restart is None
            and not offside
            and r_uv[0] > max(line - P.THROUGH_BALL_NEAR_LINE, 0.0)
            and rng.random() < P.THROUGH_BALL
        )
        if through:  # into space behind the line, for the receiver to run onto
            ahead = np.array([rng.uniform(*P.THROUGH_BALL_DEPTH), rng.normal(0.0, 3.0)])
            end = self.pos[r] + self.to_uv(team, ahead)
        end = self.inside(end)
        length = float(np.hypot(*(end - origin)))

        wide_cross = (
            restart is None
            and o_uv[0] > P.CROSS_ZONE_U
            and abs(o_uv[1]) > P.BOX_HALF_WIDTH - 2
            and r_uv[0] > GOAL_U - P.BOX_DEPTH - 4
        )
        subtype = restart if restart != "free_kick_box" else "free_kick"
        if wide_cross:
            subtype = "cross"
        h = rng.random()
        if restart == "throw_in":
            height = PassHeight.LOW
        elif restart in ("corner", "free_kick_box") or wide_cross:
            height = PassHeight.HIGH if h < 0.75 else PassHeight.LOW
        elif restart == "kick_off" or length < 22:
            height = PassHeight.GROUND if h < 0.85 else PassHeight.LOW
        elif length < 35:
            height = [PassHeight.GROUND, PassHeight.LOW, PassHeight.HIGH][
                int(np.searchsorted([0.45, 0.7], h, side="right"))
            ]
        else:
            height = PassHeight.HIGH if h < 0.75 else PassHeight.LOW
        a, b = P.PASS_SPEED_HIGH if height == PassHeight.HIGH else P.PASS_SPEED_GROUND
        flight_s = max(length / (a + b * length), 0.2)
        if height == PassHeight.HIGH:
            peak = float(np.clip(GRAVITY * flight_s**2 / 8, 2.0, 25.0))
        elif height == PassHeight.LOW:
            peak = rng.uniform(0.5, 1.5)
        else:
            peak = 0.0

        presser, press_d = self.nearest(1 - team, origin)
        p_ok = self.teams[team].pass_success - P.PASS_SUCCESS_PER_M * max(0.0, length - 10.0)
        p_ok -= 0.06 * (press_d < 3.0) + 0.05 * (height == PassHeight.HIGH) + 0.2 * wide_cross
        p_ok -= P.PASS_FINAL_THIRD_PENALTY * (self.zone(team, end) == 2)
        p_ok -= P.THROUGH_BALL_PENALTY * through
        if restart in ("kick_off", "throw_in", "goal_kick"):
            p_ok += 0.05
        p_ok = float(np.clip(p_ok, 0.15, 0.99))
        self.roles.on_pass(t, c, r, through, wide_cross, restart is None, end)

        f = Flight(origin.copy(), end, t, snap(t + flight_s), peak, "complete", by=c, to=r)
        if offside:
            f.result = "offside"
        elif height == PassHeight.HIGH:
            opp, d = self.nearest(1 - team, end)
            if d < P.AERIAL_DUEL_RADIUS:
                f.result, f.challenger = "aerial", opp
                f.receiver_wins = bool(rng.random() < P.AERIAL_RECEIVER_WINS * (0.5 + p_ok / 2))
        if f.result == "complete" and rng.random() > p_ok:
            self.fail_pass(f, team, flight_s)
        outcome = (
            Outcome.SUCCESS
            if f.result == "complete" or (f.result == "aerial" and f.receiver_wins)
            else Outcome.FAIL
        )
        self.log(
            EventType.PASS,
            t,
            c,
            subtype=subtype,
            related_player_id=r,
            start=origin,
            end=f.end,
            end_t=f.t1,
            outcome=outcome,
            height=height,
            body_part=BodyPart.OTHER if restart == "throw_in" else BodyPart.FOOT,
            restart=restart is not None,
        )
        self.flight = f
        self.mode = "flight"
        self.touch = None

    def fail_pass(self, f: Flight, team: int, flight_s: float) -> None:
        """Turn a planned completion into an interception, a ball out of play, or a loose ball."""
        rng = self.rng
        kind = rng.choice(list(P.FAIL_SPLIT), p=list(P.FAIL_SPLIT.values()))
        if kind == "out":
            out = self.over_nearest_line(f.end, P.OUT_REACH)
            if out is not None:
                stretch = np.hypot(*(out - f.start)) / max(np.hypot(*(f.end - f.start)), 1.0)
                f.result, f.end, f.to = "out", out, -1
                f.t1 = snap(f.t0 + flight_s * stretch)
                attacking_line = abs(out[0]) > P.HALF_LENGTH and self.to_uv(team, out)[0] > 0
                if attacking_line and rng.random() < P.OUT_DEFLECTED:
                    f.by, _ = self.nearest(1 - team, f.end, skip_gk=True)  # corner
                return
            kind = "loose"
        if kind == "intercepted":
            opp, s = self.nearest_to_segment(1 - team, f.start, f.end)
            s = max(s, 0.3)
            f.end = f.start + s * (f.end - f.start)
            f.t1 = snap(f.t0 + flight_s * s)
            f.to = opp
            own_box = self.to_uv(1 - team, f.end)[0] < -(GOAL_U - P.BOX_DEPTH)
            f.result = "clear" if own_box and rng.random() < P.CLEAR_IN_BOX else "intercepted"
            return
        angle = rng.uniform(0, 2 * math.pi)
        offset = rng.uniform(3.0, 8.0) * np.array([math.cos(angle), math.sin(angle)])
        f.end = self.inside(f.end + offset)
        f.result, f.to = "loose", -1

    @staticmethod
    def over_nearest_line(b: np.ndarray, reach: float) -> np.ndarray | None:
        """``b`` pushed 1 m past a line within ``reach`` metres, the touchline first."""
        lim = np.array([P.HALF_LENGTH, P.HALF_WIDTH])
        gaps = lim - np.abs(b)
        axis = 1 if gaps[1] <= reach else 0
        if gaps[axis] > reach:
            return None
        out = b.copy()
        out[axis] = np.sign(b[axis] or 1.0) * (lim[axis] + 1.0)
        return out

    def kick_loose(self, t: float, origin: np.ndarray, distance: float, by: int) -> None:
        """The ball runs loose; near a line it may run out of play."""
        angle = self.rng.uniform(0, 2 * math.pi)
        end = origin + distance * np.array([math.cos(angle), math.sin(angle)])
        result = "loose"
        if np.any(np.abs(end) > (P.HALF_LENGTH, P.HALF_WIDTH)):
            result = "out"
            end = self.over_nearest_line(end, 0.0)
        self.lose_control()
        self.flight = Flight(origin.copy(), end, t, snap(t + distance / 8.0), 0.5, result, by=by)
        self.mode = "flight"
        self.touch = None

    # --- Shots -------------------------------------------------------------------------------

    @staticmethod
    def xg(u: float, v: float, header: bool) -> float:
        dx = GOAL_U - u
        dist = math.hypot(dx, v)
        angle = max(math.atan2(2 * P.GOAL_HALF_WIDTH * dx, dx**2 + v**2 - P.GOAL_HALF_WIDTH**2), 0)
        b0, b_dist, b_angle = P.XG_COEF
        xg = 1 / (1 + math.exp(-(b0 + b_dist * dist + b_angle * angle)))
        if header:
            xg *= 0.6  # headers convert worse than kicks: our assumption
        return round(float(np.clip(xg, 0.01, 0.95)), 3)

    def shoot(self, t: float, c: int, header: bool) -> None:
        rng = self.rng
        team = int(self.team_of[c])
        origin = self.pos[c].copy()
        u, v = self.to_uv(team, origin)
        xg = self.xg(u, v, header)
        to = -1
        if rng.random() < xg:
            result = "goal"
            end_uv = np.array([GOAL_U + 0.5, rng.uniform(-3.3, 3.3)])
        else:
            result = rng.choice(list(P.SHOT_SPLIT), p=list(P.SHOT_SPLIT.values()))
            end_uv = np.array([GOAL_U + 1.0, rng.choice([-1, 1]) * rng.uniform(4.2, 12.0)])
        end = self.to_uv(team, end_uv)
        if result == "saved":
            to = int(self.members(1 - team)[0])
            end = self.pos[to].copy()
        elif result == "blocked":
            to, _ = self.nearest_to_segment(1 - team, origin, end)
            end = origin + (end - origin) / np.hypot(*(end - origin)) * rng.uniform(1.5, 4.0)
        dist = float(np.hypot(*(end - origin)))
        f = Flight(origin, end, t, snap(t + dist / 24.0), rng.uniform(0.2, 2.0), result, c, to)
        self.log(
            EventType.SHOT,
            t,
            c,
            subtype=result,
            start=origin,
            end=end,
            end_t=f.t1,
            outcome=Outcome.SUCCESS if result == "goal" else Outcome.FAIL,
            body_part=BodyPart.HEAD if header else BodyPart.FOOT,
            xg=xg,
        )
        self.flight = f
        self.mode = "flight"
        self.touch = None

    # --- Flight arrival ----------------------------------------------------------------------

    def arrive(self, t: float) -> None:
        rng = self.rng
        f = self.flight
        result = f.result
        if result == "complete":
            self.receive(t, f.to, header=f.peak_z > 2.0)
        elif result == "offside":
            self.log(EventType.OFFSIDE, t, f.to, start=f.end)
            self.free_kick(t, 1 - int(self.team_of[f.to]), f.end)
        elif result == "intercepted":
            self.gain_possession(int(self.team_of[f.to]), t, True, f.end)
            self.log(EventType.INTERCEPTION, t, f.to, start=f.end, outcome=Outcome.SUCCESS)
            self.start_touch(f.to, t)
        elif result == "clear":
            self.clearance(t, f.to, f.end)
        elif result == "aerial":
            self.log(
                EventType.DUEL,
                t,
                f.challenger,
                related_player_id=f.to,
                start=f.end,
                subtype="aerial",
                body_part=BodyPart.HEAD,
                outcome=Outcome.FAIL if f.receiver_wins else Outcome.SUCCESS,
            )
            if f.receiver_wins:
                self.receive(t, f.to, header=True)
            elif self.to_uv(int(self.team_of[f.challenger]), f.end)[0] < -(GOAL_U - P.BOX_DEPTH):
                self.clearance(t, f.challenger, f.end, BodyPart.HEAD)
            else:
                self.kick_loose(t, f.end, rng.uniform(5.0, 12.0), f.challenger)
        elif result in ("out", "wide"):
            self.ball_out(t, f.by, f.end)
        elif result == "loose":
            self.lose_control()
            self.mode = "loose"
            self.loose_since = t
            self.loose_point = f.end
        elif result == "goal":
            self.goal(t, f.by, f.end)
        elif result == "saved":
            if rng.random() < P.SAVE_TO_CORNER:
                self.ball_out(t, f.to, self.behind_goal_line(int(self.team_of[f.to])))
            else:
                self.gain_possession(int(self.team_of[f.to]), t, False, f.end)
                self.log(EventType.BALL_RECOVERY, t, f.to, subtype="save", start=f.end)
                self.start_touch(f.to, t)
        elif result == "blocked":
            if rng.random() < P.BLOCK_TO_CORNER:
                self.ball_out(t, f.to, self.behind_goal_line(int(self.team_of[f.to])))
            else:
                self.kick_loose(t, f.end, rng.uniform(3.0, 10.0), f.to)

    def goal(self, t: float, scorer: int, end: np.ndarray) -> None:
        """Log the goal, schedule the kick-off, and send the scorer's team-mates to them
        (``HUDDLE_*``)."""
        self.log(EventType.GOAL, t, scorer, start=end)
        team = int(self.team_of[scorer])
        self.score[team] += 1
        self.schedule_restart("kick_off", 1 - team, np.zeros(2), t, end)
        at = self.pos[scorer]
        spot = np.array([at[0], np.sign(at[1] or 1.0) * (P.HALF_WIDTH - 2.0)])
        gap = spot - at
        spot = at + gap * min(1.0, P.HUDDLE_RUN / max(float(np.hypot(*gap)), 1e-6))
        mates = [int(i) for i in self.members(team)[1:] if i != scorer]
        mates.sort(key=lambda i: float(np.hypot(*(self.pos[i] - at))))
        t_end = min(t + P.HUDDLE_MAX_S, self.restart.t - P.HUDDLE_BACK_S)
        self.restart.huddle = Huddle(scorer, spot, mates[: P.HUDDLE_N], t_end)

    def behind_goal_line(self, defending: int) -> np.ndarray:
        """A point just past the goal line that ``defending`` defends, off the posts."""
        v = self.rng.choice([-1, 1]) * self.rng.uniform(4.0, 10.0)
        return self.to_uv(defending, np.array([-GOAL_U - 1.0, v]))

    def receive(self, t: float, r: int, header: bool) -> None:
        where = self.flight.end
        self.log(EventType.RECEPTION, t, r, start=where, outcome=Outcome.SUCCESS)
        if self.rng.random() < P.MISCONTROL:
            self.log(EventType.BALL_LOSS, t, r, subtype="miscontrol", start=where)
            self.kick_loose(t, where, self.rng.uniform(2.0, 5.0), r)
            return
        self.gain_possession(int(self.team_of[r]), t, True, where)
        self.start_touch(r, t, header)

    def clearance(
        self, t: float, d: int, where: np.ndarray, body_part: BodyPart = BodyPart.FOOT
    ) -> None:
        rng = self.rng
        team = int(self.team_of[d])
        end_uv = self.to_uv(team, where) + np.array([rng.uniform(25, 50), rng.normal(0, 15)])
        end = self.to_uv(team, end_uv)
        if rng.random() < P.CLEAR_OUT:
            if rng.random() < P.CLEAR_OUT_CORNER:
                end_uv = np.array([-GOAL_U - 1.0, np.sign(end_uv[1] or 1.0) * rng.uniform(5, 25)])
            else:
                end_uv[1] = np.sign(end_uv[1] or 1.0) * (P.HALF_WIDTH + 1.0)
            end = self.to_uv(team, end_uv)
            result = "out"
        else:
            end = self.inside(end)
            result = "loose"
        self.log(EventType.CLEARANCE, t, d, start=where, end=end, body_part=body_part)
        dist = float(np.hypot(*(end - where)))
        self.lose_control()
        self.flight = Flight(where.copy(), end, t, snap(t + dist / 18.0), 8.0, result, by=d)
        self.mode = "flight"

    def update_loose(self, t: float) -> None:
        d = np.hypot(*(self.pos - self.loose_point).T)
        i = int(np.argmin(d))
        if d[i] < 1.0 or t >= self.loose_since + 5.0:
            self.gain_possession(int(self.team_of[i]), t, True, self.loose_point)
            self.log(EventType.BALL_RECOVERY, t, i, start=self.loose_point)
            self.start_touch(i, t)

    # --- Dead balls and restarts -------------------------------------------------------------

    def ball_out(self, t: float, toucher: int, point: np.ndarray) -> None:
        self.log(EventType.BALL_OUT, t, toucher, start=point)
        team = int(self.team_of[toucher])
        x, y = point
        if abs(x) > P.HALF_LENGTH:
            # Team k defends the goal line at x = -dir_k·52.5.
            line_owner = 0 if np.sign(x) == -self.dir[0] else 1
            if line_owner == team:
                corner = np.array([np.sign(x) * P.HALF_LENGTH, np.sign(y or 1.0) * P.HALF_WIDTH])
                self.schedule_restart("corner", 1 - team, corner, t, point)
            else:
                spot = self.to_uv(line_owner, np.array([-GOAL_U + 5.5, 0.0]))
                self.schedule_restart("goal_kick", line_owner, spot, t, point)
        else:
            spot = np.array([np.clip(x, -P.HALF_LENGTH, P.HALF_LENGTH), np.sign(y) * P.HALF_WIDTH])
            self.schedule_restart("throw_in", 1 - team, spot, t, point)

    def free_kick(self, t: float, team: int, where: np.ndarray) -> None:
        u, v = self.to_uv(team, where)
        if u > GOAL_U - P.BOX_DEPTH and abs(v) < P.BOX_HALF_WIDTH:
            u = GOAL_U - P.BOX_DEPTH - 1.0  # no penalties in v0
        spot = self.inside(self.to_uv(team, np.array([u, v])))
        self.schedule_restart("free_kick", team, spot, t, self.ball_xy[:2].copy())

    def schedule_restart(
        self, kind: str, team: int, spot: np.ndarray, t: float, ball_from: np.ndarray
    ) -> None:
        rng = self.rng
        median, sigma = P.DEAD_TIME[kind]
        delay = rng.lognormal(math.log(median), sigma)
        if rng.random() < P.LONG_STOPPAGE:
            delay += rng.uniform(*P.LONG_STOPPAGE_S)
        if kind == "goal_kick":
            taker = int(self.members(team)[0])
        elif kind == "kick_off":
            taker = int(self.members(team)[10])
        else:
            taker, _ = self.nearest(team, spot, skip_gk=True)
        self.restart = Restart(kind, team, spot, snap(t + delay), taker, ball_from.copy(), t)
        self.mode = "dead"
        self.poss_team = team
        self.flight = None
        self.touch = None
        self.end_transition(t)
        self.press = None
        self.roles.clear()

    def take_restart(self, t: float) -> None:
        r = self.restart
        self.gain_possession(r.team, t, False, r.spot)
        kind = r.kind
        if kind == "free_kick" and self.set_piece():
            kind = "free_kick_box"
        self.play_pass(t, r.taker, r.spot.copy(), restart=kind)

    # --- Shapes and ball --------------------------------------------------------------------

    def kickoff_shape(self, team: int) -> np.ndarray:
        uv = movement.shape_targets(self.slots[team], np.zeros(2), in_possession=False)
        uv[:, 0] = np.minimum(uv[:, 0], -1.0)
        if self.restart is not None and self.restart.team == team:
            uv[10] = (-0.3, 0.0)
            uv[7] = (-3.0, 4.0)
        else:
            keep = P.RESTART_DISTANCE + P.RESTART_MARGIN  # [IFAB2025, Law 8]
            r = np.hypot(*uv.T)
            push = (r < keep) & (r > 0)
            uv[push] *= (keep / r[push])[:, None]
        return uv

    def set_piece(self) -> bool:
        """The restart is a corner, or a free kick near goal (``SET_PIECE_U``, ``WALL_RANGE``)."""
        r = self.restart
        if r.kind == "corner":
            return True
        if r.kind != "free_kick":
            return False
        u, v = self.to_uv(r.team, r.spot)
        return u > P.SET_PIECE_U or math.hypot(GOAL_U - u, v) <= P.WALL_RANGE

    def set_piece_plan(self, rng: np.random.Generator) -> list[tuple[int, np.ndarray, bool]]:
        """(player, spot, holds) for everyone with a set-piece job; ``holds`` marks the
        attackers, who hold their spots (anchored) while the others settle round them.

        At a corner the attackers take ``CORNER_SPOTS`` and ``CORNER_PACK``, and two defenders
        go zonal (``CORNER_ZONAL``); at a free kick the attackers form the line
        (``FREE_KICK_LINE*``, each spot moved by ``rng``), in the order they stand across the
        pitch. Markers are matched in the same order, so that pairs do not cross, and stand 1 m
        goal-side of their attacker (the pack's on its outside shoulders,
        ``CORNER_PACK_SHOULDER``). Made once per set piece."""
        r = self.restart
        team = r.team
        att = self.members(team)
        dfn = self.members(1 - team)
        plan: list[tuple[int, np.ndarray, bool]] = []
        if r.kind == "corner":
            side = float(np.sign(self.to_uv(team, r.spot)[1]) or 1.0)
            u0, v0 = P.CORNER_PACK_AT
            n = len(P.CORNER_PACK)
            uv = [(slot, u, side * v, 0.0) for slot, u, v in P.CORNER_SPOTS]
            for k, slot in enumerate(P.CORNER_PACK):
                out = k - (n - 1) / 2.0
                v = side * (v0 + out * P.CORNER_PACK_GAP)
                uv.append((slot, u0, v, side * np.sign(out) * P.CORNER_PACK_SHOULDER))
            for slot, u, v in P.CORNER_ZONAL:
                plan.append((int(dfn[slot]), self.to_uv(team, np.array([u, side * v])), False))
        else:
            depth = GOAL_U - self.to_uv(team, r.spot)[0]
            line = float(np.clip(depth - P.FREE_KICK_LINE_GAP, *P.FREE_KICK_LINE))
            slots = [slot for slot, _, _ in P.CORNER_SPOTS] + list(P.CORNER_PACK)
            slots.sort(key=lambda s: float(self.to_uv(team, self.pos[att[s]])[1]))
            jitter = rng.uniform(-1.0, 1.0, (len(slots), 2)) * P.FREE_KICK_LINE_JITTER
            u = GOAL_U - line - 1.0
            uv = [
                (slot, u + du, v + dv, 0.0)
                for slot, v, (du, dv) in zip(slots, P.FREE_KICK_LINE_V, jitter, strict=True)
            ]
        # The taker takes the kick; the nearest free attacker goes to their spot instead.
        used = {row[0] for row in uv}
        free = [s for s in range(1, 11) if s not in used and att[s] != r.taker]
        for k, (slot, u, v, side_v) in enumerate(uv):
            if att[slot] == r.taker:
                spot = self.to_uv(team, np.array([u, v]))
                sub = min(free, key=lambda s: float(np.hypot(*(self.pos[att[s]] - spot))))
                uv[k] = (sub, u, v, side_v)
        uv.sort(key=lambda row: row[2])
        markers = sorted(P.BOX_MARKERS, key=lambda s: float(self.to_uv(team, self.pos[dfn[s]])[1]))
        for (slot, u, v, side_v), m in zip(uv, markers, strict=True):
            to_goal = np.array([GOAL_U - u, -v])
            mark = np.array([u, v + side_v]) + to_goal / np.hypot(*to_goal)
            plan.append((int(att[slot]), self.to_uv(team, np.array([u, v])), True))
            plan.append((int(dfn[m]), self.to_uv(team, mark), False))
        return plan

    def ball_at(self, t: float) -> np.ndarray:
        mode = self.mode
        if mode == "touch":
            c = self.touch.player
            v = self.vel[c]
            sp = math.hypot(*v)
            xy = self.pos[c] + (0.5 * v / sp if sp > 0.3 else 0.0)
            return np.array([xy[0], xy[1], 0.0])
        if mode == "flight":
            f = self.flight
            s = min(max((t - f.t0) / max(f.t1 - f.t0, 1e-9), 0.0), 1.0)
            xy = f.start + s * (f.end - f.start)
            return np.array([xy[0], xy[1], 4 * f.peak_z * s * (1 - s)])
        if mode == "loose":
            return np.array([self.loose_point[0], self.loose_point[1], 0.0])
        r = self.restart
        s = min(max((t - r.t_dead) / 3.0, 0.0), 1.0)
        xy = r.ball_from + s * (r.spot - r.ball_from)
        return np.array([xy[0], xy[1], 0.0])

    # --- Main loop ---------------------------------------------------------------------------

    def update(self, t: float) -> None:
        if self.transition is not None and t >= self.transition[1]:
            self.end_transition(t)
        if self.press is not None:
            presser = self.press[0]
            if t >= self.press[1] or self.to_uv(1 - presser, self.ball_xy[:2])[0] > -P.THIRD + 7:
                self.press = None
        mode = self.mode
        if mode == "dead":
            r = self.restart
            close = np.hypot(*(self.pos[r.taker] - r.spot)) < 1.5
            if t >= r.t and (close or t >= r.t + 10.0):
                self.take_restart(t)
        elif mode == "touch":
            self.update_touch(t)
        elif mode == "flight":
            if t >= self.flight.t1 - 1e-9:
                self.arrive(t)
        elif mode == "loose":
            self.update_loose(t)

    def update_shape_weights(self) -> None:
        """Move each team's in-possession shape weight towards 1 or 0 (``SHAPE_SWITCH_S``)."""
        holder = self.poss_team if self.poss_team is not None else self.last_team
        for k in (0, 1):
            goal = 1.0 if holder == k else 0.0
            tau = P.SHAPE_SWITCH_S[0] if goal > self.shape_w[k] else P.SHAPE_SWITCH_S[1]
            self.shape_w[k] += (goal - self.shape_w[k]) * (1.0 - math.exp(-P.DT / tau))

    def follow_ball(self, t: float) -> None:
        """The ball's position this frame, the lagged copy the shapes follow (``SHAPE_LAG_S``) and
        the shape weights."""
        self.ball_xy = self.ball_at(t)
        self.shape_ball += (self.ball_xy[:2] - self.shape_ball) * (
            1.0 - math.exp(-P.DT / P.SHAPE_LAG_S)
        )
        self.update_shape_weights()

    def move(self, t: float) -> np.ndarray:
        """Every player takes one movement step (roles, push-apart, motion model); returns the
        purpose codes of this frame."""
        target, cap, purpose, calm, anchored = self.roles.targets(t)
        keep = P.SEPARATION_DEAD if self.mode == "dead" else P.SEPARATION_TEAM
        wall = self.roles.wall_mask()
        push = movement.push_apart(self.pos, self.team_of, anchored, self.vel, keep, wall)
        a0, s0 = self.a0, self.s0
        if self.physiology is not None:
            a0, s0 = a0 * self.physiology.accel_mult, s0 * self.physiology.speed_mult
        self.pos, self.vel = movement.step(self.pos, self.vel, target, cap, a0, s0, calm, push)
        return purpose

    def run_period(self, period: int, n_frames: int, kick_team: int) -> PeriodFrames:
        self.period = period
        home_dir = 1.0 if self.teams[0].attacks_positive_x_in_period_1 else -1.0
        if period == 2:
            home_dir = -home_dir
        self.dir = [home_dir, -home_dir]
        self.last_team = None
        self.poss_team = kick_team
        self.transition = None
        self.press = None
        self.touch = None
        self.flight = None
        self.restart = Restart("kick_off", kick_team, np.zeros(2), 0.0, 10 + 11 * kick_team,
                               np.zeros(2), 0.0)  # fmt: skip
        self.mode = "dead"
        self.pos = np.concatenate([self.to_uv(k, self.kickoff_shape(k)) for k in (0, 1)])
        self.pos[self.restart.taker] = 0.0
        self.vel = np.zeros((22, 2))
        self.ball_xy = np.zeros(3)
        self.shape_ball = np.zeros(2)
        self.shape_w = np.full(2, 0.5)
        self.roles.clear()
        body = self.physiology
        if body is not None:
            body.start_period(period)

        pos = np.empty((n_frames, 22, 2))
        ball = np.empty((n_frames, 3))
        alive = np.empty(n_frames, dtype=bool)
        possession = np.empty(n_frames, dtype=np.int8)
        purpose = np.empty((n_frames, 22), dtype=np.int8)
        self.log(EventType.PERIOD_START, 0.0)
        subs: list[tuple[int, int, str]] = []
        if self.pending:  # half-time substitutions, before the kick-off
            subs += self.substitute_due(0.0, 0)
        for k in range(n_frames):
            t = round(k / P.FRAME_RATE_HZ, 1)
            self.update(t)
            if self.pending and self.mode == "dead":
                subs += self.substitute_due(t, k)
            self.follow_ball(t)
            pos[k] = self.pos
            ball[k] = self.ball_xy
            alive[k] = self.mode != "dead"
            possession[k] = -1 if self.poss_team is None else self.poss_team
            purpose[k] = self.move(t)
            if body is not None:
                body.step(np.hypot(self.vel[:, 0], self.vel[:, 1]), t)
                if k % round(P.FRAME_RATE_HZ) == 0:
                    body.record(t)
        t_end = round((n_frames - 1) / P.FRAME_RATE_HZ, 1)
        self.end_transition(t_end)
        self.log(EventType.PERIOD_END, t_end)
        return PeriodFrames(period, pos, ball, alive, possession, purpose, subs)

    def substitute_due(self, t: float, k: int) -> list[tuple[int, int, str]]:
        """Make the substitutions due by now (the ball is dead); returns (frame, slot, id)."""
        clock = self.clock(t)
        due = [s for s in self.pending if s.clock_s <= clock]
        made = []
        for sub in due:
            self.pending.remove(sub)
            i, new = sub.slot, sub.player
            self.log(EventType.SUBSTITUTION, t, i, related_player_id=new.id)
            self.sub_log.append((self.period, t, i, self.ids[i], new.id))
            self.ids[i] = new.id
            self.a0[i], self.s0[i] = new.params.a0, new.params.s0
            self.roles.runs.pop(i, None)
            self.roles.declined.pop(i, None)
            if self.physiology is not None:
                self.physiology.substitute(i, new.params)
            made.append((k, i, new.id))
        return made
