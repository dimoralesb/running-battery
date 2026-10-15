"""Tuning constants for the generator (BUILD_PLAN §4, "Thu 15" to "Sun 18").

Every number has a source ("synthesis §x" is docs/RESEARCH_SYNTHESIS.md) or is labelled "our
assumption". Most "our assumption" values are knobs. The movement knobs were calibrated on
2026-10-15 with fatigue off (``sim.batch``, 90–120 seeds): distance, >5.5 m/s and >7 m/s per
position against synthesis §4.2, running by phase [Allen2026b, Table 5], and time in speed bands
against IDSSE (``sim.idsse``). The match-flow knobs are tuned to the interim targets in
``secondwind.sim.summary.TARGETS``. Saturday's fatigue model will move the totals a little; the
batch should be re-run then.
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
# Calm movement (holding the shape, repositioning, walking while the ball is dead) is not a
# maximal effort: α is scaled by CALM_ALPHA and the arrival time is CALM_ARRIVE_TAU. Our
# assumption, tuned to the IDSSE acceleration bands (PLAN §2.5).
CALM_ALPHA = 0.5
CALM_ARRIVE_TAU = 2.5

# --- Role behaviours and run purposes ------------------------------------------------------------

# A high-intensity run: above 5.5 m/s (19.8 km/h) for at least 1 s [Ju2022, p.974].
HI_SPEED = 5.5
HI_MIN_S = 1.0
# Effort levels as a share of S0, by how urgent a movement is. Our assumption, tuned with the
# rest of the movement knobs (module docstring).
DRIFT_SPEED = 0.42  # holding the team shape
DEAD_SPEED = 0.40  # walking back into shape while the ball is dead
CHASE_SPEED = 0.90  # receiver, presser, interceptor, loose ball
RUN_SPEED = 0.88  # in-possession runs: in behind, overlap, into the box, support
SHOW_SPEED = 0.70  # coming short to receive
ONSIDE_SPEED = 0.60  # hurrying back from an offside position
# Full effort is V = S0 (synthesis §4.10). The hardest runs use a share of it: runs in behind
# and chasing a through ball (BEHIND_EFFORT), tracking a runner (TRACK_EFFORT), support runs on
# a counter-attack (COUNTER_SUPPORT_EFFORT), overlaps (OVERLAP_EFFORT) and recovery runs from
# far out of position (RECOVERY_EFFORT). Our assumption, tuned to sprint distance and top speed
# per position (synthesis §4.2; [SilvaH2025, Table 1]).
BEHIND_EFFORT = 1.0
TRACK_EFFORT = 0.95
COUNTER_SUPPORT_EFFORT = 0.95
OVERLAP_EFFORT = 0.86
RECOVERY_EFFORT = 0.92
SPRINT_RUN_S = (3.0, 6.0)  # how long a sprint run may last, s. Our assumption.
# Work rate per position: the wanted speed of every run and ball role (not calm movement) is
# multiplied by this, then capped at S0. Position differences come from role behaviour, not
# from different physical settings (PLAN §7, decision 3). Our assumption, fitted to HID and
# sprint distance per position (synthesis §4.2) on 90–120 seeds. Sprint distance is sensitive: 1%
# more effort gives about 5–10% more distance above 7 m/s.
POSITION_EFFORT = {
    Position.GK: 1.008,
    Position.CB: 0.945,
    Position.FB: 1.0,
    Position.DM: 1.04,
    Position.CM: 1.043,
    Position.AM: 1.008,
    Position.WM: 1.02,
    Position.CF: 0.974,
}
# Defenders (CB, FB) who track an opponent running in behind: the nearest TRACKERS, aiming
# TRACK_GOAL_SIDE metres goal-side of where the runner is going. Our assumption.
TRACKERS = 1
TRACK_GOAL_SIDE = 2.0
# A player who receives on the run keeps up to this much of their speed while carrying the
# ball (run with ball). Our assumption.
CARRY_MOMENTUM = 0.85
# Shape runs: past SHAPE_RUN_GAP metres from their shape target, a player starts a labelled run
# (recovery run, covering, pushing up, support) until the gap is back under SHAPE_RUN_END. Its
# speed grows with the gap at the start, from SHAPE_RUN_MIN to SHAPE_RUN_SPEED at SHAPE_RUN_FULL
# metres; a recovery run (not goal-side of the ball) in danger (DANGER_U) grows from
# SHAPE_RUN_SPEED to RECOVERY_EFFORT. Our assumption.
SHAPE_RUN_GAP = 9.0
SHAPE_RUN_FULL = 25.0
SHAPE_RUN_END = 3.0
SHAPE_RUN_MIN = 0.50
SHAPE_RUN_SPEED = 0.84
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
OVERLAP_CHANCE = 0.75  # full-back overlaps a wide player on the ball, middle or final third
BOX_RUN_CHANCE = 0.85  # each forward breaks into the box when the ball is wide in the final third
BEHIND_CHANCE = 0.25  # a forward near the offside line runs in behind as the pass is played
SUPPORT_RUNNERS = 2  # midfielders (not the DM) who sprint up in support in a positive transition
# On a positive transition, each forward ahead of the ball sprints towards goal with this
# chance (positive transitions hold the most sprinting [Bortnik2022, Fig. 3]), COUNTER_DEPTH
# metres ahead. These runs may go beyond the offside line; passers avoid offside team-mates
# (OFFSIDE_PASS_WEIGHT). Our assumption, tuned to forwards' sprint distance (synthesis §4.2).
COUNTER_RUN_CHANCE = 0.55
COUNTER_DEPTH = (15.0, 30.0)
# How far beyond the offside line a run in behind aims, m. Our assumption.
BEHIND_DEPTH = (15.0, 30.0)
RUN_S = (2.0, 4.5)  # length of a triggered run, s
# Exploit space: when a team-mate has the ball outside their own third, one free forward may
# run EXPLOIT_LENGTH metres into space towards goal at RUN_SPEED (Move to Receive / Exploit
# Space [Ju2022, Table 1]). Our assumption, tuned to the purpose mix and in-possession running.
EXPLOIT_CHANCE = 0.25
EXPLOIT_LENGTH = (12.0, 22.0)
# Support in settled play: when a team-mate carries the ball in the middle or final third more
# than MID_SUPPORT_GAP metres ahead of a free midfielder (DM, CM, AM), that midfielder may run
# up to about MID_SUPPORT_BEHIND metres behind the ball at RUN_SPEED (Support Play [Ju2022,
# Table 1]). Our assumption, tuned to midfielders' distance (synthesis §4.2).
MID_SUPPORT_CHANCE = 0.55
MID_SUPPORT_GAP = 15.0
MID_SUPPORT_BEHIND = 10.0
# Pressing high: when an opponent gets the ball in their own half, the nearest free forward
# within PRESS_REACH metres closes them down with this chance. Our assumption, tuned to the
# purpose mix (forwards close down most [Ju2022, p.978–980]).
PRESS_RUN_CHANCE = 0.4
PRESS_REACH = 20.0
# Central midfielders (DM, CM) close down a carrier in the middle third on their side of
# halfway with this chance (Close Down/Press is one of the CMP actions [Ju2022, p.978–980]).
# Our assumption, tuned to their HID (synthesis §4.2).
MID_PRESS_CHANCE = 0.3
# Recovery runs reach full effort only when there is danger: the ball in the team's own half
# (u < DANGER_U in the team's frame) or the opponent on a counter-attack. Our assumption, tuned
# to the purpose mix [Ju2022, p.975] and the HID by phase [Allen2026b, Table 5].
DANGER_U = 0.0

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
# Without the ball the front players stay this many metres higher than the block's shape: they
# are the first line of the press and do not drop all the way. Our assumption, tuned to
# forwards' distance (synthesis §4.2) and their purpose mix (forwards close down more and
# cover less than defenders [Ju2022, p.978–980]).
OUT_OF_POSSESSION_HOLD = {Position.CF: 8.0, Position.AM: 6.0, Position.WM: 3.0}
# A team switches between its in- and out-of-possession shapes gradually: the weight of the
# in-possession shape moves towards 1 (ball won) with time constant SHAPE_SWITCH_S[0] and
# towards 0 (ball lost) with SHAPE_SWITCH_S[1]. Losing the ball is answered faster. Our
# assumption, tuned to the distance per position (synthesis §4.2).
SHAPE_SWITCH_S = (4.0, 1.5)
# The shape follows a lagged copy of the ball: its reference point closes the gap to the ball
# with time constant SHAPE_LAG_S, so a long pass moves the block over a few seconds, not in one
# jump. Our assumption, tuned to the IDSSE jogging share (PLAN §2.5).
SHAPE_LAG_S = 1.5
# Small repositioning: every WANDER_S seconds each player picks a new spot about WANDER_SD
# metres (SD per axis) from their shape or set-piece position, in play and while the ball is
# dead. Our assumption, tuned to dead-ball running, 63 m/min [Allen2026b, Table 5, derived],
# and the IDSSE walking share.
# Central midfielders adjust the most, centre-backs and forwards the least: the size is per
# position, tuned to the distance per position (synthesis §4.2).
WANDER_SD = {
    Position.GK: 0.8,
    Position.CB: 1.6,
    Position.FB: 2.3,
    Position.DM: 3.2,
    Position.CM: 3.2,
    Position.AM: 1.8,
    Position.WM: 1.4,
    Position.CF: 1.0,
}
WANDER_S = (4.0, 10.0)

# Goalkeeper. Our assumption, tuned to the goalkeeper's distance, 4,720 m (synthesis §4.2), and
# the IDSSE goalkeeper speed bands. Without the ball the keeper stands on the line from the goal
# centre to the ball, GK_DEPTH metres off the goal line: GK_DEPTH[0] when the ball is within
# GK_DEPTH_FROM metres of goal, plus GK_DEPTH_SLOPE per metre further out, at most GK_DEPTH[1].
# With the ball the keeper stays GK_BEHIND_LINE metres behind the back line, at most
# GK_MAX_OFF metres from the goal line. A pass or cross landing within GK_CLAIM_REACH metres of
# the goal centre makes the keeper come for it.
GK_DEPTH = (2.0, 16.0)
GK_DEPTH_FROM = 10.0
GK_DEPTH_SLOPE = 0.2
GK_BEHIND_LINE = 20.0
GK_MAX_OFF = 24.0
GK_CLAIM_REACH = 26.0

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
OFFSIDE_PASS_WEIGHT = 0.045
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
