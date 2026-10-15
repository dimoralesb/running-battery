"""Tuning constants for the generator (BUILD_PLAN §4, "Thu 15" and "Fri 16").

Every number has a source ("synthesis §x" is docs/RESEARCH_SYNTHESIS.md) or is labelled "our
assumption". Most "our assumption" values are knobs tuned so that the match totals land on the
interim targets in ``secondwind.sim.summary.TARGETS``; Sunday's calibration replaces them.
"""

from __future__ import annotations

from secondwind.schema import Position

# --- Time and pitch -----------------------------------------------------------------------------

FRAME_RATE_HZ = 10.0  # synthesis §7.1
DT = 1.0 / FRAME_RATE_HZ

HALF_LENGTH = 52.5  # 105 x 68 m pitch [Bassek2025, Box 3]
HALF_WIDTH = 34.0
GOAL_HALF_WIDTH = 3.66  # 7.32 m goal [IFAB2025, Law 1]
BOX_DEPTH = 16.5  # penalty area, same source as the goal
BOX_HALF_WIDTH = 20.16
THIRD = HALF_LENGTH / 3  # 35 m thirds: the middle third is |u| < 17.5 m

# --- Match length -------------------------------------------------------------------------------

# 99.5 ± 2.9 min including added time, 2024/25 [Allen2025, Table 2].
MATCH_MINUTES_MEAN = 99.5
MATCH_MINUTES_SD = 2.9
MATCH_MINUTES_CLIP_SD = 3.0  # draws clipped at ±3 SD: our assumption
# Share of the added time that goes to the first half. Our assumption: the papers give only the
# total, and second halves usually get more added time (substitutions, more stoppages).
FIRST_HALF_ADDED_SHARE = (0.25, 0.40)

# --- Players ------------------------------------------------------------------------------------

# Hidden "true" values, one shared prior for every outfield position (PLAN §7, decision 3).
# CS 3.7 m/s (13.3 km/h), range 3.2–4.2 [synthesis §3.2.3]; SD = range / 4 is our assumption.
CS_MEAN, CS_SD, CS_RANGE = 3.7, 0.25, (3.2, 4.2)
# D′ 180 m, range 100–300 [synthesis §3.2.3]; SD 54 m [Sutcliffe2025, Fig. 2].
D_PRIME_MEAN, D_PRIME_SD, D_PRIME_RANGE = 180.0, 54.0, (100.0, 300.0)
# A0 ~ N(7.4, 0.5) m/s², range 6.6–8.4; S0 ~ N(9.3, 0.45) m/s, range 8.4–10.3 [Morin2021, Table 1].
A0_MEAN, A0_SD, A0_RANGE = 7.4, 0.5, (6.6, 8.4)
S0_MEAN, S0_SD, S0_RANGE = 9.3, 0.45, (8.4, 10.3)
# Two-pool truth model [Chorley2022; Chorley2023, Eq. 6b–6c; synthesis §3.2.4]. Drawn today but
# not used until Saturday.
FAST_FRACTION_RANGE = (0.40, 0.50)
TAU_FAST_RANGE = (15.0, 35.0)  # s
TAU_SLOW_RANGE = (400.0, 500.0)  # s, when walking
# Club test values = truth × (1 + e), e ~ N(0, SD), clipped at ±3 SD. Written only with
# --club-tests (PLAN §3.2), but always drawn so a seed gives the same match either way.
# A0 5.4% and S0 3.3% are the measurement noise of the profile [Morin2021, Table 1]. CS 5% and
# D′ 15% are our assumption, larger for D′ because it depends strongly on the test method
# (synthesis §3.2.3).
TEST_ERROR_SD = dict(cs=0.05, d_prime=0.15, a0=0.054, s0=0.033)

# --- Motion model (synthesis §4.10) ------------------------------------------------------------

# Equation of motion dv/dt = α(V·n − v) [Narizuka2023, Eq. 3], with α = A0/S0 per player and
# V = S0 at full effort (synthesis §4.10, derived). Lower efforts use a lower V: our assumption.
# Speeding up is capped at a_max(v) = A0·(1 − v/S0) [Morin2021, p.2]. The model allows hard
# reversals at speed, so braking gets its own cap of about 5–6 m/s² (synthesis §4.10, our
# assumption). Turning (sideways acceleration) uses the same cap: our assumption.
BRAKE_MAX = 5.5
TURN_MAX = 5.5
# Time to close the gap to a moving target: τ ≈ S0/A0 ≈ 1.25 s (synthesis §3.6, derived).
ARRIVE_TAU = 1.25

# --- Role behaviours and run purposes ------------------------------------------------------------

# A high-intensity run: above 5.5 m/s (19.8 km/h) for at least 1 s [Ju2022, p.974].
HI_SPEED = 5.5
HI_MIN_S = 1.0
# Effort levels as a share of S0, by how urgent a movement is. Our assumption, tuned on Sunday.
DRIFT_SPEED = 0.42  # holding the team shape
DEAD_SPEED = 0.40  # walking back into shape while the ball is dead
CHASE_SPEED = 0.90  # receiver, presser, interceptor, loose ball
RUN_SPEED = 0.88  # in-possession runs: in behind, overlap, into the box, support
SHOW_SPEED = 0.70  # coming short to receive
ONSIDE_SPEED = 0.60  # hurrying back from an offside position
# Shape runs: past SHAPE_RUN_GAP metres from their shape target, a player starts a labelled run
# (recovery run, covering, pushing up, support) until the gap is back under SHAPE_RUN_END. Its
# speed grows with the gap at the start, from SHAPE_RUN_MIN to SHAPE_RUN_SPEED at SHAPE_RUN_FULL
# metres; a recovery run (not goal-side of the ball) is always at SHAPE_RUN_SPEED. Our assumption.
SHAPE_RUN_GAP = 9.0
SHAPE_RUN_FULL = 25.0
SHAPE_RUN_END = 3.0
SHAPE_RUN_MIN = 0.50
SHAPE_RUN_SPEED = 0.82
SHAPE_RUN_MAX_S = 8.0
# A defender this close to where a pass will arrive closes the receiver down. Our assumption.
CLOSE_DOWN_REACH = 15.0
# Closing down aims this far goal-side of the opponent, not at the opponent. Our assumption.
PRESS_GAP = 1.5
# Cover: the second defender stands this far behind the presser, on the line to goal. Our
# assumption.
COVER_DEPTH = 8.0
# Chances that a run starts when a team-mate gets the ball (per touch), and how long it lasts.
# Our assumption.
SHOW_CHANCE = 0.35  # one team-mate comes short to offer a pass
OVERLAP_CHANCE = 0.45  # full-back overlaps a wide player on the ball, middle or final third
BOX_RUN_CHANCE = 0.85  # each forward breaks into the box when the ball is wide in the final third
BEHIND_CHANCE = 0.30  # a forward near the offside line runs in behind as the pass is played
SUPPORT_RUNNERS = 2  # midfielders who sprint up in support during a positive transition
RUN_S = (2.0, 4.5)  # length of a triggered run, s

# --- Position noise (synthesis §3.1) -------------------------------------------------------------

# Optical tracking error 0.06–0.18 m [Bassek2025, p.7]; σ ≈ 0.1 m per axis (synthesis §3.1).
# Drawn after the match from the same generator, so the match itself never changes with it.
NOISE_SIGMA = 0.1
# Dropouts: a player is missing from a few frames now and then. The IDSSE validation found no
# missing frames [Bassek2025, p.8]; we add them only to test the estimator's gap filling. Rate
# and length are our assumption.
DROPOUTS_PER_MIN = 0.2  # per player
DROPOUT_S = (0.2, 2.0)

# --- Formation ----------------------------------------------------------------------------------

# 4-2-3-1 slots: (position, u, v) in the team's attacking frame (u towards the opponent's goal,
# v to the team's left), relative to the team's centre line. Our assumption.
FORMATION_4231: list[tuple[Position, float, float]] = [
    (Position.GK, 0.0, 0.0),  # goalkeeper is placed separately
    (Position.CB, -13.0, 9.0),
    (Position.CB, -13.0, -9.0),
    (Position.FB, -9.0, 25.0),
    (Position.FB, -9.0, -25.0),
    (Position.DM, -3.0, 7.0),
    (Position.CM, -1.0, -7.0),
    (Position.AM, 9.0, 0.0),
    (Position.WM, 8.0, 24.0),
    (Position.WM, 8.0, -24.0),
    (Position.CF, 18.0, 0.0),
]
SHIRTS = {
    Position.GK: [1],
    Position.CB: [5, 4],
    Position.FB: [3, 2],
    Position.DM: [6],
    Position.CM: [8],
    Position.AM: [10],
    Position.WM: [11, 7],
    Position.CF: [9],
}

# Team shape: centre line follows the ball, block is deeper and narrower without the ball.
# Our assumption.
SHAPE_IN_POSSESSION = dict(line_gain=0.55, line_offset=6.0, depth=1.0, width=1.05, ball_pull=0.25)
SHAPE_OUT_OF_POSSESSION = dict(
    line_gain=0.5, line_offset=-10.0, depth=0.65, width=0.7, ball_pull=0.4
)
PRESS_LINE_PUSH = 12.0  # m, how much higher the block stands in a high press

# --- Match flow ---------------------------------------------------------------------------------
# All "our assumption" values below are tuned to the interim targets (summary.TARGETS).

# Time on the ball between receiving and releasing it, s: lognormal(median, sigma).
TOUCH_MEDIAN, TOUCH_SIGMA = 1.9, 0.6
GK_TOUCH_MEDIAN = 4.0
CARRY_SPEED = (2.5, 5.5)  # m/s while carrying in settled play
CARRY_SPEED_TRANSITION = (5.0, 7.0)  # m/s on a counter-attack
CARRY_ANGLE_SD = (0.7, 0.9, 1.4)  # rad around "straight at goal", by third
MIN_CARRY_LENGTH = 1.0  # m; shorter touches are not logged as carries

# Passes. Completion about 80% [Fang2024, Fig. 1]; the model below is our assumption.
PASS_LENGTH_PREF, PASS_LENGTH_SD = 16.0, 9.0  # m, receiver choice
PASS_FORWARD_GAIN = (0.10, 0.08, 0.02)  # per metre towards goal, by third (own, middle, final)
PASS_FORWARD_GAIN_TRANSITION = 0.22
PASS_BASE_SUCCESS = 0.93
# Offside [IFAB2025, Law 11]: a receiver in the opponent's half, ahead of both the ball and the
# second-last opponent, when the ball is played; not from throw-ins, goal kicks or corners.
# About 2.3 per match [Bassek2025, Fig. 3; approx.]. Attackers hold their shape this far
# onside, and passers avoid offside team-mates, the more so the clearer the offside (weight
# falls by e every OFFSIDE_SEEN metres beyond the line): our assumption, the weight tuned to the
# count.
ONSIDE_MARGIN = 1.0  # m
OFFSIDE_PASS_WEIGHT = 0.09
OFFSIDE_SEEN = 1.0  # m
# Through balls: a pass into space up to 15 m beyond a receiver standing near the offside line.
# Offside is judged when the ball is played, so the run behind is legal. Our assumption.
THROUGH_BALL = 0.7  # chance, when the receiver is within THROUGH_BALL_NEAR_LINE of the line
THROUGH_BALL_NEAR_LINE = 4.0  # m
THROUGH_BALL_DEPTH = (5.0, 15.0)  # m ahead of the receiver
THROUGH_BALL_PENALTY = 0.10  # lower completion than a pass to feet
PASS_SUCCESS_PER_M = 0.004  # lost per metre beyond 10 m
PASS_SUCCESS_TEAM_SD = 0.02  # team quality spread, gives possession shares away from 50%
PASS_SPEED_GROUND = (9.0, 0.22)  # m/s = a + b·length
PASS_SPEED_HIGH = (11.0, 0.25)
PASS_FINAL_THIRD_PENALTY = 0.08  # passes into a crowded final third fail more often
BOX_RECEIVER_WEIGHT = 0.8  # in the final third, fewer passes go straight into the box
FAIL_SPLIT = dict(intercepted=0.42, out=0.50, loose=0.08)  # how a failed ground pass fails
OUT_REACH = 22.0  # m; a pass failing this close to a line goes out of play
OUT_DEFLECTED = 0.10  # share of those over the opponent's goal line a defender touched last
AERIAL_DUEL_RADIUS = 8.0  # m; an opponent this close to a high pass's landing spot contests it
AERIAL_RECEIVER_WINS = 0.5
MISCONTROL = 0.03  # chance a reception bounces loose

# Ground duels against the ball carrier.
DUEL_PER_TOUCH = 0.18
DUEL_REACH = 4.0  # m; the challenger must be this close
DUEL_CHALLENGER_WINS = 0.5
DUEL_TACKLER_KEEPS = 0.4  # otherwise the ball runs loose
FOUL_PER_DUEL = 0.15
CARD_PER_FOUL = 5.3 / 22  # 5.3 cautions per 22 fouls [Bassek2025, Fig. 3; approx., derived]
PRESSURE_RADIUS = 5.0  # m; the nearest opponent within this distance logs a pressure

# Shots. xG per shot 0.11 ± 0.15 [Bassek2025, p.6]. The logistic xG curve and the shot rate
# are our assumption, tuned to about 24 shots per match [Bassek2025, p.6].
SHOT_RANGE = 30.0  # m from the goal centre
SHOT_RATE = 0.85  # chance of shooting on release, at the goal line; falls with distance
SHOT_RATE_SCALE = 16.0  # m
XG_COEF = (-1.1, -0.11, 1.6)  # intercept, per m of distance, per rad of goal-mouth angle
SHOT_SPLIT = dict(saved=0.30, wide=0.45, blocked=0.25)  # non-goals [Bassek2025, Fig. 3; approx.]
SAVE_TO_CORNER = 0.4
BLOCK_TO_CORNER = 0.4
CROSS_ZONE_U = 30.0  # m from the centre line, and wider than the box

# Clearances when a pass into the box is intercepted.
CLEAR_IN_BOX = 0.6
CLEAR_OUT = 0.45  # chance the clearance goes out of play
CLEAR_OUT_CORNER = 0.4  # and, if so, that it goes behind for a corner (else a throw-in)

# Dead-ball time before each restart, s: lognormal(median, sigma). Our assumption, tuned so the
# ball is in play about 55% of the match [Kavanagh2024, p.80; Allen2026b, Table 2].
DEAD_TIME = {
    "kick_off": (60.0, 0.15),  # after a goal
    "throw_in": (14.0, 0.3),
    "goal_kick": (23.0, 0.25),
    "corner": (32.0, 0.25),
    "free_kick": (26.0, 0.3),
}
LONG_STOPPAGE = 0.10  # chance of an extra stoppage (injury, VAR, substitution) at a dead ball
LONG_STOPPAGE_S = (30.0, 90.0)

# Transitions: about 50 ± 11 per match, about 10 s each; positive 10.9 ± 3.9 s, negative
# 9.3 ± 3.4 s [Bortnik2022, Tables 1–2]. The chance that an open-play turnover starts one is
# our assumption, tuned to the count. The drawn length is longer than 10 s because many end
# early (turnover, ball out); tuned so the realised length is about 10 s (our assumption).
TRANSITION_CHANCE = 0.32
TRANSITION_S = (15.0, 4.5, 5.0, 27.0)  # drawn length: mean, SD, min, max
# High press: chance the defending team presses when the opponent has the ball in its own
# third; lasts at most about 10 s (high-press spells 9.8 ± 3.7 s [Bortnik2022, Table 2]).
PRESS_CHANCE = (0.25, 0.55)  # range of team styles, our assumption
PRESS_MAX_S = 10.0
