"""Tuning constants for the generator (BUILD_PLAN §4, "Thu 15" to "Sun 18").

Every number has a source ("synthesis §x" is docs/RESEARCH_SYNTHESIS.md) or is labelled "our
assumption". Most "our assumption" values are knobs. The movement knobs were calibrated on
2026-10-15 with fatigue off (``sim.batch``, 90–120 seeds): distance, >5.5 m/s and >7 m/s per
position against synthesis §4.2, running by phase [Allen2026b, Table 5], and time in speed bands
against IDSSE (``sim.idsse``). The match-flow knobs are tuned to the interim targets in
``runningbattery.sim.summary.TARGETS``. On 2026-10-16 the fatigue model (``physiology.py``) and the
shared match tempo were added and calibrated on 120–240 seeds with fatigue on (``sim.batch``,
``sim.fatigue_checks``), and the work rate and two run chances re-fitted: the totals of real
matches include fatigue.
"""

from __future__ import annotations

from runningbattery.schema import Position

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

# Hidden "true" values, one shared prior for every outfield position (PLAN §7, decisions 3 and 13):
# a typical professional. CS 4.1 ± 0.3 m/s (14.8 km/h), clipped at ±2 SD to 3.5–4.7. Derivation
# (synthesis §3.2.3): professionals' VO₂max 57.6 ml/kg/min and an oxygen cost of running of about
# 0.196 ml/kg/m (derived: oxygen use at the anaerobic threshold divided by its speed) [Modric2020,
# Table 1]; CS lies at 70–90% of VO₂max [Jones2017, p.S67], i.e. 3.4 / 3.9 / 4.4 m/s at 70 / 80 /
# 90% (derived); professionals are well trained, so 85% (our assumption): 4.16, rounded to 4.1.
# SD: the spread between professionals' threshold speeds, 0.21–0.26 m/s [Modric2020, Table 1],
# widened to 0.3 for the uncertainty in the 70–90% (our assumption). Until 2026-10-17 the
# generator drew from a university prior, CS 3.7 ± 0.25 m/s (now ``engine.params.PRIORS``).
CS_MEAN, CS_SD, CS_RANGE = 4.1, 0.3, (3.5, 4.7)
# D′ 180 m, range 100–300 [synthesis §3.2.3]; SD 54 m [Sutcliffe2025, Fig. 2].
D_PRIME_MEAN, D_PRIME_SD, D_PRIME_RANGE = 180.0, 54.0, (100.0, 300.0)
# A0 ~ N(7.4, 0.5) m/s², range 6.6–8.4; S0 ~ N(9.3, 0.45) m/s, range 8.4–10.3 [Morin2021, Table 1].
A0_MEAN, A0_SD, A0_RANGE = 7.4, 0.5, (6.6, 8.4)
S0_MEAN, S0_SD, S0_RANGE = 9.3, 0.45, (8.4, 10.3)
# Two-pool truth model [Chorley2022; Chorley2023, Eq. 6b–6c; synthesis §3.2.4], used by
# ``physiology.py``: the share of D′ in the fast pool and each pool's recharge time standing
# still (synthesis §3.2.4 gives the slow pool's when walking; the two differ by about 4%,
# derived from Chorley2023, Eq. 6c).
FAST_FRACTION_RANGE = (0.40, 0.50)
TAU_FAST_RANGE = (15.0, 35.0)  # s
TAU_SLOW_RANGE = (400.0, 500.0)  # s
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
# Push-apart: players do not stand on the same spot. Before each step, team-mates' targets
# closer than SEPARATION_TEAM are moved apart, so two players are not sent to the same spot.
# Then a player closer than their separation to someone else adds (separation − gap) /
# SEPARATION_TAU m/s, straight away from them, to the velocity they want, at most
# SEPARATION_MAX m/s in total. The push may turn or slow a moving player but never makes them
# faster than they want, and the acceleration caps above still apply. Team-mates keep about
# 1.5–2 m apart. Opponents may come closer, about 0.8–1 m: markers
# stand 1 m goal-side of attackers at set pieces, and defenders close down to PRESS_GAP. The
# player on the ball, the receiver and a restart taker are not pushed. Our assumption.
SEPARATION_TEAM = 2.0
SEPARATION_OPP = 0.9
SEPARATION_TAU = 0.25  # s
SEPARATION_MAX = 6.0  # m/s (21.6 km/h)
# Team-mates are judged at their closest approach within SEPARATION_LOOKAHEAD seconds, at their
# current velocities, and pushed apart along the line between them at that moment (sideways for
# paths that cross), so that crossing paths move apart before they meet. Our assumption, with
# SEPARATION_TAU and SEPARATION_MAX tuned towards IDSSE [Bassek2025], where team-mates come
# within 1 m in 0.20% of in-play player-frames (our measure, sim.spacing, 2026-10-15). Ours,
# 120 seeds: 0.83% with no look-ahead, 0.45% judged at their positions 1 s on (which misses
# paths that cross within the second), 0.17% at closest approach. Decision 39 (team-mates within
# 0.7 m in 5 clips of the site): SEPARATION_TEAM 1.8 → 2.0 m, SEPARATION_TAU 0.4 → 0.25 s,
# SEPARATION_MAX 4 → 6 m/s and the look-ahead 1.0 → 1.2 s, with the push blended between the
# line between them now and at closest approach and their speed along their path kept: 0.01%
# within 1 m in play (240 seeds), fewer than IDSSE, so that no clip shows two team-mates on top
# of each other.
SEPARATION_LOOKAHEAD = 1.2  # s
# While the ball is dead, team-mates may stand closer: SEPARATION_DEAD for targets and the push
# (never two on one spot). This lets corner packs, walls and goal huddles form. IDSSE has a
# team-mate within 1 m in 3.85% of dead-ball player-frames [Bassek2025; our measure, 2026-10-15],
# but that includes substitutions, injuries and crowds round the referee, which we do not
# simulate; we aim for about 1–2%. Our assumption.
SEPARATION_DEAD = 0.8

# --- Role behaviours and run purposes ------------------------------------------------------------

# A high-intensity run: above 5.5 m/s (19.8 km/h) for at least 1 s [Ju2022, p.974].
HI_SPEED = 5.5
HI_MIN_S = 1.0
# Effort levels as a share of S0, by how urgent a movement is. Our assumption, tuned with the
# rest of the movement knobs (module docstring).
DRIFT_SPEED = 0.42  # holding the team shape
DEAD_SPEED = 0.40  # walking back into shape while the ball is dead
CHASE_SPEED = 0.90  # receiver, presser, interceptor, loose ball
LOOSE_CHASERS = 1  # per team: the nearest player goes for a loose ball (was 2; decision 37)
RUN_SPEED = 0.88  # in-possession runs: in behind, overlap, into the box, support
SHOW_SPEED = 0.70  # coming short to receive
ONSIDE_SPEED = 0.60  # hurrying back from an offside position
# Full effort is V = S0 (synthesis §4.10). The hardest runs use a share of it: runs in behind
# and chasing a through ball (BEHIND_EFFORT), tracking a runner (TRACK_EFFORT), support runs on
# a counter-attack (COUNTER_SUPPORT_EFFORT), overlaps (OVERLAP_EFFORT) and recovery runs from
# far out of position (RECOVERY_EFFORT). Our assumption, tuned to sprint distance and top speed
# per position (synthesis §4.2; [SilvaH2025, Table 1]).
BEHIND_EFFORT = 1.0
# Since decision 42 these four are fitted with POSITION_EFFORT by sim.calibrate (the values by hand
# before it: 0.95, 0.95, 0.86 and 0.92); RECOVERY_EFFORT stays at least SHAPE_RUN_SPEED.
TRACK_EFFORT = 0.947
COUNTER_SUPPORT_EFFORT = 0.920
OVERLAP_EFFORT = 0.770
RECOVERY_EFFORT = 0.840
SPRINT_RUN_S = (3.0, 6.0)  # how long a sprint run may last, s. Our assumption.
# A run that heads back within TURN_S seconds of being above HI_SPEED the other way (more than
# 90° round) goes no faster than SHAPE_RUN_MIN until then: he turns first. Our assumption
# (decision 41: a run in behind or an overlap, the ball lost, and a sprint straight back;
# sprint-turns, above 6 m/s one way then the other within 4 s, were 0.75–2.60 per player-hour
# against 0–1.04 in IDSSE).
TURN_S = 3.5
# Work rate per position: the wanted speed of every run and ball role (not calm movement) is
# multiplied by this, then capped at S0. Position differences come from role behaviour, not
# from different physical settings (PLAN §7, decision 3). Our assumption, fitted to HID and
# sprint distance per position (synthesis §4.2) on 90–240 seeds; re-fitted on 2026-10-15 after
# the push-apart rule, its look-ahead, and the closest-approach look-ahead and dead-ball
# structures (set pieces, goal huddle). Sprint distance is sensitive: 1% more effort gives
# about 5–10% more distance above 7 m/s. One knob cannot fit both for wide midfielders (their
# HID runs high when their sprint distance is on target), so WM sits where both are about ±5%.
# Centre-forwards came close to the same trade-off once they defended the near post at corners
# (CORNER_ZONAL): HID +9%, sprint +11% before the re-fit. Re-fitted on 2026-10-16 with fatigue
# on (the totals of real matches include fatigue): tired players skip, shorten and slow runs,
# so every position needs a higher work rate than with fatigue off. DM and CM trimmed 0.5% with
# substitutions on (2026-10-16): their sprint was +7% (240 seeds; fresh substitutes add sprinting).
# Re-fitted on 2026-10-17 for the professional prior (CS 4.1 m/s, with the tank re-fitted): fewer
# runs are skipped, so sprint rose (team +13%); FB +0.2%, DM −0.1%, CM +0.3%, AM −0.8% against the
# values before, which brings HID within ±5% except FB (the one-knob trade-off) and the team's
# sprint back to about +7% (120 and 240 seeds). Decision 38 (shots on clear chances, the ball
# rolling to its player): fewer turnovers cut midfield high-speed running 1-3 points, so DM, CM
# and AM rose 0.3, 0.9 and 0.5% (60 seeds). Decision 39 (the stronger push-apart, keepers held
# within GK_MAX_OFF): midfielders' high-speed running fell 3-4 points (DM −7.2%, CM −6.8%, 60
# seeds), so MID_SUPPORT_CHANCE and MID_PRESS_CHANCE rose and CB, FB, DM, CM and AM 0.4, 0.4,
# 0.6, 0.7 and 1.6% (120 and 240 seeds): high-speed running per position within ±5%, sprint
# distance FB +13%, DM and CM +10%, team +7% (240 seeds). Decision 40 (set-piece jobs paced
# to the restart, below 5 m/s; no sprint carried on after the whistle): high-speed running per
# position fell about 2 points, all of it while the ball was dead (in play, per minute, it did
# not move), FB −6.1% and CM −5.7% (120 seeds), so FB and CM rose 0.9 and 0.6%. With box
# carries aimed at goal too (same decision): high-speed running per position within ±5% (FB
# −4.2, DM −4.4, CM −4.6, AM −4.2%), sprint distance FB +17%, DM +8%, CM +11%, team +7% (240
# seeds). Decision 41 (trackers follow the runner and stop with the pass; no sprint straight back,
# TURN_S): the decoy runs tracked to an empty spot had been a third of centre-backs' high-speed
# running (CB −33%, FB −14%, DM, CM and AM −8 to −10%), so CB, FB, DM, CM, AM and CF rose 13.9,
# 4.5, 0.8, 0.3, 1.6 and 2.2% (CB and FB at 1.10, the most WALL_SPEED allows below), with
# COUNTER_DROP_* and defenders following runs into space: high-speed running per position within
# ±5.3% (CB −1.5, FB −4.0, DM −5.3, CM −3.3, AM −0.5%), sprint distance FB +16%, DM +9%, CM +12%,
# team +7% (120 seeds; decision 40 on the same seeds +16, +8, +13 and +6%). Decision 42: no more
# tuning by hand. sim.calibrate fits these with the efforts of the hardest runs (TRACK_EFFORT and
# the three after it), DUEL_PER_TOUCH, TRANSITION_CHANCE, SHAPE_RUN_GAP and SHAPE_LAG_S to the
# per-position targets, running by phase, event counts and the IDSSE speed bands and dithering
# (least squares on a fitted response surface, trust-region steps; 3,700 matches on seeds from
# 10001, never the 1–120 check seeds). The keepers' work rate rose most (0.99 → 1.156): low
# passes cut out since decision 41 took a sixth of the balls they came for, and the rest were
# shorter (their high-speed running 27 → 18 m a match); with the dead-ball jog capped after the
# work rate, CB and FB are no longer held at 1.10.
POSITION_EFFORT = {
    Position.GK: 1.156,
    Position.CB: 1.132,
    Position.FB: 1.126,
    Position.DM: 1.060,
    Position.CM: 1.100,
    Position.AM: 1.108,
    Position.WM: 1.089,
    Position.CF: 0.995,
}
# Defenders (CB, FB) who track an opponent running in behind: the nearest TRACKERS follow him,
# TRACK_GOAL_SIDE metres goal-side of where he is now, while the pass is in flight or he has the
# ball; they stop when his run ends, the pass reaches someone else, or the ball runs loose or is
# won. Our assumption (decision 41): before, the tracker sprinted for 3–6 s to a fixed point
# goal-side of where the runner was heading, whatever happened to the pass, then sprinted
# straight back out (sprint-turns 0.75–2.60 per player-hour against 0–1.04 in IDSSE).
TRACKERS = 1
TRACK_GOAL_SIDE = 2.0
# A player who receives on the run keeps up to this much of their speed while carrying the
# ball (run with ball). Our assumption.
CARRY_MOMENTUM = 0.85
# Shape runs: past SHAPE_RUN_GAP metres from their shape target, a player starts a labelled run
# (recovery run, covering, pushing up, support) until the gap is back under SHAPE_RUN_END. Its
# speed grows with the gap at the start, from SHAPE_RUN_MIN to SHAPE_RUN_SPEED at SHAPE_RUN_FULL
# metres; a recovery run (not goal-side of the ball) in danger (DANGER_U) grows from
# SHAPE_RUN_SPEED to RECOVERY_EFFORT. Out of possession, a run mostly up the pitch, back up to the
# line, goes no faster than SHAPE_RUN_MIN unless the team is pressing (decision 41: a defender
# who had dropped deep sprinted back out at 7 m/s). Our assumption.
SHAPE_RUN_GAP = 10.05  # 9.0 before decision 42 (sim.calibrate: dithering)
# On the opponents' counter-attack (a transition), or caught upfield of the ball out of
# possession, a defender (CB, FB) starts his shape run from COUNTER_DROP_GAP metres, at
# COUNTER_DROP_SPEED of S0 or more. Our assumption (decision 41): with decoy runs no longer
# tracked to an empty spot, centre-backs' high-speed running was 30% short; this, and following
# runs into space (roles.TRACKED), is where real centre-backs do theirs.
COUNTER_DROP_GAP = 3.0
COUNTER_DROP_SPEED = 0.80
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
# Our assumption. OVERLAP_CHANCE was 0.75 with fatigue off: a tired full-back who skips an
# overlap does not get it offered again, so with fatigue on more are offered (2026-10-16).
SHOW_CHANCE = 0.35  # one team-mate comes short to offer a pass
OVERLAP_CHANCE = 0.9  # full-back overlaps a wide player on the ball, middle or final third
BOX_RUN_CHANCE = 0.85  # each forward breaks into the box when the ball is wide in the final third
# a forward near the offside line runs in behind as a forward pass is played; 0.25 before decision
# 37 limited the run to forward passes and short of the keeper and the penalty spot, raised to
# keep forwards' and centre-backs' sprint distance (synthesis §4.2) on 60 seeds
BEHIND_CHANCE = 0.9
SUPPORT_RUNNERS = 2  # midfielders (not the DM) who sprint up in support in a positive transition
# On a positive transition, each forward ahead of the ball sprints towards goal with this
# chance (positive transitions hold the most sprinting [Bortnik2022, Fig. 3]), COUNTER_DEPTH
# metres ahead. These runs may go beyond the offside line; passers avoid offside team-mates
# (OFFSIDE_PASS_WEIGHT). Our assumption, tuned to forwards' sprint distance (synthesis §4.2);
# 0.55 before decision 37 stopped these runs short of the keeper and the penalty spot.
COUNTER_RUN_CHANCE = 0.6
COUNTER_DEPTH = (15.0, 30.0)
# How far beyond the offside line a run in behind aims, m. Our assumption. A run in behind
# starts only on a pass at least BEHIND_PASS_FORWARD metres forward (the receiver can then play
# it on), and aims no deeper than BEHIND_KEEPER_GAP metres short of the opponents' goalkeeper
# nor nearer goal than BEHIND_GOAL_GAP (the penalty spot): the space is between the back line
# and the keeper (decision 37). Our assumption.
BEHIND_DEPTH = (15.0, 30.0)
BEHIND_KEEPER_GAP = 2.0
BEHIND_GOAL_GAP = 11.0
BEHIND_PASS_FORWARD = 5.0
RUN_S = (2.0, 4.5)  # length of a triggered run, s
# Exploit space: when a team-mate has the ball outside their own third, one free forward may
# run EXPLOIT_LENGTH metres into space towards goal at RUN_SPEED (Move to Receive / Exploit
# Space [Ju2022, Table 1]). Our assumption, tuned to the purpose mix and in-possession running;
# 0.25 before decision 37, raised with BEHIND_CHANCE for attacking midfielders' running.
EXPLOIT_CHANCE = 0.35
EXPLOIT_LENGTH = (12.0, 22.0)
# Support in settled play: when a team-mate carries the ball in the middle or final third more
# than MID_SUPPORT_GAP metres ahead of a free midfielder (DM, CM, AM), that midfielder may run
# up to about MID_SUPPORT_BEHIND metres behind the ball at RUN_SPEED (Support Play [Ju2022,
# Table 1]). Our assumption, tuned to midfielders' distance (synthesis §4.2); 0.55 with fatigue
# off, raised with fatigue on like OVERLAP_CHANCE (2026-10-16); 0.65 before decision 37, which
# cut midfielders' close-down runs; 0.85 before decision 39 (see POSITION_EFFORT).
MID_SUPPORT_CHANCE = 0.95
MID_SUPPORT_GAP = 15.0
MID_SUPPORT_BEHIND = 10.0
# Pressing high: when an opponent gets the ball in their own half, the nearest free forward
# within PRESS_REACH metres closes them down with this chance. Our assumption, tuned to the
# purpose mix (forwards close down most [Ju2022, p.978–980]).
# Nobody presses a carrier a team-mate is already within PRESS_COVERED metres of, and a
# close-down run ends when the ball reaches a new carrier (it followed the old one; decision
# 37). Our assumption. The chances were 0.4 and 0.3 (MID_PRESS_CHANCE) before decision 37,
# raised so that forwards and midfielders keep their high-speed running.
PRESS_RUN_CHANCE = 0.7
PRESS_REACH = 20.0
PRESS_COVERED = 5.0
# Central midfielders (DM, CM) close down a carrier in the middle third on their side of
# halfway with this chance (Close Down/Press is one of the CMP actions [Ju2022, p.978–980]).
# Our assumption, tuned to their HID (synthesis §4.2); 0.7 before decision 39 (see
# POSITION_EFFORT).
MID_PRESS_CHANCE = 0.8
# Recovery runs reach full effort only when there is danger: the ball in the team's own half
# (u < DANGER_U in the team's frame) or the opponent on a counter-attack. Our assumption, tuned
# to the purpose mix [Ju2022, p.975] and the HID by phase [Allen2026b, Table 5].
DANGER_U = 0.0

# The movement calibration with fatigue off, as at 81f023d (2026-10-15): used only when fatigue
# and the tempo are both off (``--no-fatigue --no-tempo``), which then gives the generator's
# matches from before either existed, file for file. The no-fatigue control (``--no-fatigue``)
# keeps the values above, so that it differs from its fatigue-on twin only in fatigue.
PRE_FATIGUE = {
    "POSITION_EFFORT": {
        Position.GK: 1.004,
        Position.CB: 0.955,
        Position.FB: 1.005,
        Position.DM: 1.053,
        Position.CM: 1.045,
        Position.AM: 1.006,
        Position.WM: 1.017,
        Position.CF: 0.948,
    },
    "OVERLAP_CHANCE": 0.75,
    "MID_SUPPORT_CHANCE": 0.55,
}

# --- Match tempo --------------------------------------------------------------------------------

# The two teams' running moves together: home and away totals correlate at r = 0.68–0.75 for
# total, >5.5 m/s and >7 m/s distance [Allen2026a, abstract]. One tempo per match, drawn from
# N(1, TEMPO_SD) and clipped at ±TEMPO_CLIP_SD SD, multiplies both teams' work rate
# (POSITION_EFFORT). Our assumption, TEMPO_SD tuned to that correlation and to the spread of
# team totals [Allen2025, Figs 2–3].
TEMPO_SD = 0.03
TEMPO_CLIP_SD = 3.0

# --- Substitutions (match.py, rosters.py) ------------------------------------------------------

# Up to five substitutes, in at most three stoppages in play plus half-time [IFAB2025, Law 3].
# How many a team uses: our assumption (no five-substitute-era data, synthesis §8.2, point 8).
SUBS_CHOICES = (3, 4, 5)
SUBS_WEIGHTS = (0.2, 0.35, 0.45)
# Substitution windows on the match clock, min: entry times 57, 71 and 81 min in the
# three-substitute era, the first at 58 min in the EPL, and most substitutions at half-time or
# in the 60th–85th min [Myers 2012 and Bradley 2014 via Hills2018, Table 1]. A window
# drawn before HALF_TIME_SUB_BEFORE is made at half-time. SUB_WINDOW_SD, the clip and the subs
# per window (for 3, 4 and 5 substitutes) are our assumption.
SUB_WINDOWS_MIN = (58.0, 71.0, 81.0)
SUB_WINDOW_SD = (8.0, 6.0, 5.0)
SUB_WINDOW_CLIP = (40.0, 90.0)
HALF_TIME_SUB_BEFORE = 47.0
SUBS_PER_WINDOW = {3: (1, 1, 1), 4: (2, 1, 1), 5: (2, 2, 1)}
# Who goes off: like for like, never the goalkeeper; attackers, wide and central midfielders
# more often than defenders [Bradley 2014 via Hills2018, Table 1]. The weights are our
# assumption. Drawn before kick-off, so the no-fatigue control makes the same substitutions.
SUB_WEIGHT = {
    Position.GK: 0.0,
    Position.CB: 0.5,
    Position.FB: 0.8,
    Position.DM: 1.0,
    Position.CM: 1.5,
    Position.AM: 2.0,
    Position.WM: 2.5,
    Position.CF: 2.5,
}
# A substitution waits for the next stoppage [IFAB2025, Law 3]. The replaced player walks briskly
# (SUB_OFF_SPEED of S0) to the halfway line by the benches' touchline (SUB_ENTRY_Y, 1 m in from
# it), SUB_ENTRY_X metres into the half his team defends, and leaves there; his substitute comes
# on at that spot and jogs to his place in the shape at WALL_SPEED, until within SHAPE_RUN_GAP of
# it (at most SUB_MAX_S after the substitution was due); the restart waits for the replaced
# player to leave, not for the substitute to arrive. Law 3 has the
# replaced player leave at the nearest point unless the referee says otherwise; at the halfway
# line, the engine slot the two share moves on without a jump (our simplification). Half-time
# substitutes line up for the kick-off. The substitute is fresh, with their own hidden values.
# Our assumption (decision 41: the substitute appeared on the replaced player's spot,
# mid-pitch). Substitutes do more high-intensity running per minute than whole-match players
# (+15 to +27% [Bradley2013, Table IV; Bradley 2014 via Hills2018]); here that comes only from
# their fresh state, no extra work rate (our assumption, checked in sim.fatigue_checks).
SUB_ENTRY_Y = -(HALF_WIDTH - 1.0)
SUB_ENTRY_X = 1.0
SUB_OFF_SPEED = 0.4
SUB_MAX_S = 60.0

# --- Hidden physiology and fatigue (physiology.py; PLAN §2.3, layer 3) ---------------------------

# The pools refill at rest over the half-time interval, at most 15 min [IFAB2025, Law 7].
HALF_TIME_S = 900.0
# Tank: whole-match energy, 1 when fresh; the chance of a hard run is multiplied by it. It falls
# by 1 for every TANK_M metres run above the player's CS (the running that drains the pools), so
# players who run hard more often fade more, as in the Premier League, where only the players
# with the most first-half high-intensity running ran less in the second half (−12%)
# [Bradley2013, p.4]. Fatigue late in a match may come from low glycogen in many muscle fibres
# [Mohr2005]. At half-time the tank gets back TANK_HALF_TIME_REFILL of what it lost. Our
# assumption, both calibrated together: high-intensity running about 21% lower in the last
# 15 min than in the first 15 [Bradley2009, Fig. 2], while running above 5.5 m/s and sprinting
# are about the same in both halves [Bradley2009, p.162] (PLAN §2.5: within ±10%). A smaller
# refill puts more of the decline into the second half; a larger one, less into the last 15 min.
# Re-fitted on 2026-10-17 for the professional prior (CS 4.1 m/s; was 2000 m and 0.5 with CS
# 3.7): a higher CS leaves fewer metres above it and the pools rarely run low, so the tank now
# carries most of the late decline (sweeps of 120 seeds: 1400 / 1100 / 1000 / 850 m gave −13 / −17
# / −21 / −19% in the last 15 min; a refill of 0.5 put sprinting −12% in the second half).
TANK_M = 850.0
TANK_HALF_TIME_REFILL = 0.65
# After repeated hard efforts the slow pool refills 40–85% more slowly [Chorley2022; synthesis
# §3.2.4]: its time constant is multiplied by 1 + SLOW_TAU_PER_TANK × (1 − tank), +60% at a tank
# of 0.7. Our assumption (the middle of that range, at about the tank of the final minutes).
SLOW_TAU_PER_TANK = 2.0
# Start of the second half: muscle temperature falls about 2 °C over half-time [Mohr2005], and
# high-intensity running is lower in the first 10 min of the second half than of the first
# [Bradley2013, p.4]. The chance of a hard run is cut by DIP at the kick-off, fading to 0 over
# DIP_S. Our assumption.
DIP = 0.10
DIP_S = 600.0
# What the state changes. The chance that a player makes a hard run (run_choice_mult) is
# pool term × tank × (1 − dip). The pool term is 1 while the two pools hold at least POOL_FREE
# of D′ (in our matches they hold 0.78 on average, 0.62 at the 10th percentile, with no fatigue
# effect; our measure, 2026-10-16) and falls in proportion below: 1 − POOL_GAIN × (POOL_FREE −
# left) / POOL_FREE. A run decision (roles.Roles.start) with a wanted speed above HARD_RUN_SPEED
# (high-intensity running starts at 4 m/s [14.4 km/h] [Bradley2009, p.160]) is skipped with
# chance 1 − run_choice_mult: while tired (TIRED_BELOW), players skip about a third of their
# hard covering, recovery and close-down runs (sim.fatigue_checks, 2026-10-16), within the
# 22–45% drops after peak periods [Ju2022, p.975]. Our assumption. Kept with the professional
# prior (2026-10-17), although the pools now run low far less often: POOL_FREE and POOL_GAIN set
# where a tired moment starts in metres of D′, so changing them would change the label.
POOL_GAIN = 1.0
POOL_FREE = 0.75
HARD_RUN_SPEED = 4.0
# Short-term tiredness x = 1 − pool term (after intense spells; the tank does not count, since
# late in a match players make fewer hard runs but top speed barely changes [Bradley2009,
# p.163]): a run that is made lasts (1 − SHORTEN × x) of its planned time, every run and ball
# role is (1 − SLOW × x) slower, and carries are (1 − CARRY_SLOW × x) slower, so also shorter.
# After a peak period efforts are 23% shorter, 32% briefer and 3% slower, and carries fewer,
# shorter and slower [Fang2024, Table 2, Fig. 1], but most of that is there with no fatigue at all
# (sim.fatigue_checks, no-fatigue control), so the gains are small. Our assumption. Passing is
# left alone (PLAN §7, decision 5).
SHORTEN = 0.3
SLOW = 0.03
CARRY_SLOW = 0.3
# Late in a match players still make their decisive sprints: sprinting is about the same in
# both halves [Bradley2009, p.162] while high-intensity running falls [Fig. 2], and fatigue shows
# in the 4–5.5 m/s volume, accelerations and recovery time between efforts (synthesis §3.5). So
# the tank does not cut runs wanted at DECISIVE_EFFORT of S0 or more (runs in behind, tracking a
# runner, support on a counter-attack); the pools do (sprinting drops after peak periods
# [Leifsson2024, Table 1]). Our assumption.
DECISIVE_EFFORT = 0.95
# A player who skipped a shape run (recovery run, covering, pushing up, support) is asked again
# SHAPE_DECLINE_S later if still out of position; a skipped triggered run is not offered again.
# A shape run lasts until the gap has closed, usually a few seconds, not its SHAPE_RUN_MAX_S cap.
# Our assumption.
SHAPE_DECLINE_S = 5.0
# Capacity: top speed (S0) falls by TOP_SPEED_PER_TANK × (1 − tank) and acceleration (A0) by
# ACCEL_PER_TANK × (1 − tank), each at most CAPACITY_MAX_LOSS. Match top speed barely changes
# (7.65 vs 7.59 m/s [27.5 vs 27.3 km/h], −0.8%, not significant) [Bradley2009, p.163]; 10 m
# sprint times, mostly acceleration, are about 3.5% slower after a match [SilvaJR2018, Table 5].
# Our assumption: at the median tank at the final whistle, top speed is 0.9% and acceleration
# 3.75% lower (tank 0.7 with CS 3.7 on 2026-10-16: 0.03 and 0.125; about 0.6 with the
# professional prior and the re-fitted tank, 2026-10-17: 0.025 and 0.105).
TOP_SPEED_PER_TANK = 0.025
ACCEL_PER_TANK = 0.105
CAPACITY_MAX_LOSS = 0.05
# Two truth labels (decided 2026-10-16), each where its part of the hidden state alone cuts the
# chance of a hard run by at least a quarter. Our assumption, at the low end of the drops in
# covering, recovery runs and pressing after peak periods, 22–45% [Ju2022, p.975].
# - Tired moment (truth.json ``tired``): the pool term below TIRED_BELOW, short-term tiredness
#   after intense spells. About 5% of outfield player-seconds, 7 spells per player and match,
#   median 19 s (90 seeds, our measure).
# - Late-match fatigue: the tank below LATE_TANK_BELOW (from the ``tank`` series): none before
#   the 30th minute, about half of the last 15 min.
# One label on run_choice_mult (< 0.75) was tired 32% of the time and two thirds of the last
# 15 min, so the late minutes swamped the tired moments, which made precision and recall easy to
# inflate.
TIRED_BELOW = 0.75
LATE_TANK_BELOW = 0.75

# --- Validation spread (PLAN §2.6, point 3) ---------------------------------------------------

# With ``vary`` (the validation batch, ``--vary``) each match draws its own assumptions, uniform
# in these ranges, so the estimator is judged across them, not at one setting [Qin2025, §2.2;
# RuizPinto2026, Table 3]. They go into truth.json ``settings``. The ranges are our assumption,
# around the defaults above, except where noted (tank and capacity ranges moved with their
# defaults on 2026-10-17: about ×0.7–×1.4 and ±0.2 around them). The truth labels (TIRED_BELOW,
# LATE_TANK_BELOW) stay fixed: they define what is scored.
VARY = {
    "tank_m": (600.0, 1200.0),
    "tank_half_time_refill": (0.45, 0.85),
    # +40 to +85% slower slow-pool refill at a tank of 0.7 [Chorley2022; synthesis §3.2.4]
    "slow_tau_per_tank": (1.33, 2.83),
    "dip": (0.05, 0.15),
    "dip_s": (300.0, 900.0),
    "pool_free": (0.65, 0.85),
    "pool_gain": (0.7, 1.3),
    "shorten": (0.15, 0.45),
    "slow": (0.0, 0.06),
    "carry_slow": (0.15, 0.45),
    "top_speed_per_tank": (0.0, 0.05),
    "accel_per_tank": (0.05, 0.16),
    "noise_sigma_m": (0.03, 0.10),
}
# Players in a varied match come from a wider prior than the estimator's (CS 4.1 ± 0.3 m/s,
# 3.5–4.7; D′ 180 ± 54 m, 100–300; PLAN §3.2), so some true values lie outside it: SDs × 1.5 and
# wider ranges (CS ± 3.2 prior SDs, as for the university prior before 2026-10-17: 3.7 ± 0.8),
# and wider pool settings. Our assumption.
VARY_PLAYERS = {
    "cs_sd": 0.45,
    "cs_range": (3.15, 5.05),
    "d_prime_sd": 81.0,
    "d_prime_range": (70.0, 380.0),
    "fast_fraction_range": (0.35, 0.55),
    "tau_fast_range": (10.0, 45.0),
    "tau_slow_range": (350.0, 600.0),
}

# --- Position noise (synthesis §3.1) -------------------------------------------------------------

# White Gaussian noise, σ per axis. Optical tracking against VICON is off by 0.06–0.18 m
# [Bassek2025, p.7], but that includes slow, systematic error, which does not show up in speed
# and acceleration (our reading). σ = 0.05 m of white noise matches IDSSE's acceleration bands
# through our pipeline; 0.1 m (synthesis §3.1) put four bands 3–5.5 percentage points off (our
# calibration, 2026-10-15). Sensitivity runs use 0.05, 0.1, 0.3 and 1.0 m (BUILD_PLAN §3).
# Drawn after the match from the same generator, so the match itself never changes with it.
NOISE_SIGMA = 0.05
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
# jump. Our assumption, tuned to the IDSSE jogging share (PLAN §2.5); 1.5 before decision 42
# fitted it (sim.calibrate) with SHAPE_RUN_GAP to the IDSSE dithering, shape runs that chase a
# target swinging back with the ball.
SHAPE_LAG_S = 1.292
# Small repositioning: every WANDER_S seconds each player picks a new spot about WANDER_SD
# metres (SD per axis) from their shape or set-piece position, in play and while the ball is
# dead. Our assumption, tuned to dead-ball running, 63 m/min [Allen2026b, Table 5, derived],
# and the IDSSE walking share.
# Central midfielders adjust the most, centre-backs and forwards the least: the size is per
# position, tuned to the distance per position (synthesis §4.2).
WANDER_SD = {
    Position.GK: 0.95,
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
# the goal centre makes the keeper come for it. Since decision 39 no target of his, a claim or a
# loose ball he chases is further than GK_MAX_OFF from his goal line (24 m before; his clips showed
# him 25-26 m out while his team defended), and WANDER_SD[GK] rose from 0.8 to 0.95 m, which
# keeps his distance: high-speed running 28 m a match (240 seeds; 37 m before).
GK_DEPTH = (2.0, 16.0)
GK_DEPTH_FROM = 10.0
GK_DEPTH_SLOPE = 0.2
GK_BEHIND_LINE = 20.0
GK_MAX_OFF = 22.5
# Within GK_BRAKE_M of that limit a keeper moves as on a run (``movement.step``), not with the
# calm drift's slow braking, so that he stops at it (decision 41: 25 m off his line while
# defending, in a clip). Our assumption.
GK_BRAKE_M = 3.0
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
# Where a pass is cut out: the first point along it the interceptor can reach before the ball,
# running at INTERCEPT_SPEED after INTERCEPT_REACT_S (our assumption). A ball that arrives more
# than BALL_REACH metres from the player who is to take it rolls on to him at BALL_ROLL_SPEED
# (as a loose ball does, about 8 m/s), at most BALL_ROLL_MAX times, instead of jumping to his
# feet (decision 38: the ball moved 4-7 m in 0.1 s at receptions and interceptions). Our
# assumption.
INTERCEPT_SPEED = 6.0  # m/s
INTERCEPT_REACT_S = 0.3
BALL_REACH = 1.0  # m
BALL_ROLL_SPEED = 8.0  # m/s
BALL_ROLL_MAX = 3
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
# A pass in flight that comes within CUT_OUT_REACH metres of an outfield opponent while low (under
# CUT_OUT_Z metres, from CUT_OUT_EDGE_S after the kick to CUT_OUT_EDGE_S before it arrives) is
# cut out: intercepted if he is within CUT_OUT_CONTROL of its path (in his own penalty area,
# cleared), otherwise deflected loose, a few metres on. Our assumption (decision 41: a pass's
# outcome was fixed at the kick, and 6.7% of completed passes rolled past an opponent within
# 0.6 m).
CUT_OUT_REACH = 0.6  # m
CUT_OUT_CONTROL = 0.4  # m
CUT_OUT_Z = 1.0  # m
CUT_OUT_EDGE_S = 0.3

# Ground duels against the ball carrier: from a random moment of the touch, the nearest opponent
# within DUEL_ENGAGE goes in for the ball, holding the carrier up for up to DUEL_HOLD_S seconds,
# and the duel (or the foul) happens once he is within DUEL_REACH of both the carrier and the
# ball; if the carrier releases it first, there is none.
# An aerial duel's challenger, picked at the kick (AERIAL_DUEL_RADIUS), contests the ball only if
# he is within DUEL_REACH of it when it arrives. About 1.5 m, a stride and a leg's reach: 1.3 m,
# so that tracking noise on two players keeps it under 1.5. The challenger runs at the pace that
# gets him there (``roles.targets``). Our assumption (decision 41: duels were decided from up to
# 4 m, aerial ones up to 7 m, with no contact). DUEL_PER_TOUCH was 0.18 before it: fewer
# challengers reach the ball, so more go in (duels per match, summary.TARGETS).
DUEL_PER_TOUCH = 0.416  # 0.36 before decision 42 (sim.calibrate)
DUEL_ENGAGE = 4.0  # m
DUEL_HOLD_S = 1.5
DUEL_APPROACH = 0.65  # share of S0: going in for the ball is not a sprint
DUEL_REACH = 1.3  # m
DUEL_CHALLENGER_WINS = 0.5
DUEL_TACKLER_KEEPS = 0.4  # otherwise the ball runs loose
FOUL_PER_DUEL = 0.15
CARD_PER_FOUL = 5.3 / 22  # 5.3 cautions per 22 fouls [Bassek2025, Fig. 3; approx., derived]
PRESSURE_RADIUS = 5.0  # m; the nearest opponent within this distance logs a pressure

# Shots. xG per shot 0.11 ± 0.15 [Bassek2025, p.6]. The logistic xG curve and the shot rate
# are our assumption, tuned to about 24 shots per match [Bassek2025, p.6].
SHOT_RANGE = 30.0  # m from the goal centre
SHOT_RATE = (
    0.33  # chance of shooting on release, lane blocked, at the goal line; falls with distance
)
SHOT_RATE_SCALE = 16.0  # m
# A shooting lane is blocked when an outfield opponent is goal-side of the ball within
# SHOT_LANE_HALF metres of the line from the ball to the goal centre. With a clear lane the
# chance is SHOT_RATE_CLEAR up to SHOT_CLOSE metres out, falling with SHOT_CLEAR_SCALE beyond;
# inside SHOT_CLOSE metres it is at least SHOT_CLOSE_MIN even when blocked. A player with a clear
# lane who does not shoot carries on at goal for SHOT_CARRY_ON_S seconds and decides again, at
# most SHOT_CARRY_ON_MAX times, instead of passing back (decision 38: a player through on goal
# passed backwards); still clear after the last of them, he shoots (decision 42: 3 of 18 clear
# chances in the demo matches ended in a pass back after two carry-ons). Our assumption, tuned
# with SHOT_RATE to the shots per match above.
SHOT_LANE_HALF = 8.0  # m
SHOT_RATE_CLEAR = 0.95
SHOT_CLEAR_SCALE = 33.0  # m: about 0.7 at 18 m and 0.55 at 25 m
SHOT_CLOSE = 8.0  # m
SHOT_CLOSE_MIN = 0.8
SHOT_CARRY_ON_S = (0.5, 1.0)
SHOT_CARRY_ON_MAX = 2
XG_COEF = (-1.1, -0.11, 1.6)  # intercept, per m of distance, per rad of goal-mouth angle
SHOT_SPLIT = dict(saved=0.30, wide=0.45, blocked=0.25)  # non-goals [Bassek2025, Fig. 3; approx.]
SAVE_TO_CORNER = 0.4
BLOCK_TO_CORNER = 0.4
CROSS_ZONE_U = 30.0  # m from the centre line, and wider than the box

# Set pieces: a corner, or a free kick within WALL_RANGE metres of the goal centre or more than
# SET_PIECE_U metres upfield (in the attackers' frame). Six attackers go forward and six
# defenders (BOX_MARKERS, slot indices) mark them, 1 m goal-side. Our assumption.
SET_PIECE_U = 25.0
BOX_MARKERS = [1, 2, 3, 4, 5, 6]
# Corner, taken from the attackers' left (v > 0; mirrored from the right): (slot index, u, v) of
# the attackers at the near post, the far post, near the penalty spot and the edge of the box,
# and a pack of two (CORNER_PACK) side by side, CORNER_PACK_GAP metres apart, round
# CORNER_PACK_AT near the six-yard line, marked from their outside shoulders
# (CORNER_PACK_SHOULDER metres out). The pack is the crowd in the box: with a pack of three and
# its markers, corners alone gave team-mates within 1 m in 2.5% of dead-ball player-frames, more
# than the 1–2% we aim for in all (SEPARATION_DEAD; sim.spacing, 30 seeds). Our assumption.
CORNER_SPOTS = [(6, 49.5, 3.5), (9, 48.0, -5.0), (2, 43.5, -6.0), (7, 36.0, -4.0)]
CORNER_PACK = [1, 10]
CORNER_PACK_AT = (45.5, -1.0)
CORNER_PACK_GAP = 0.9
CORNER_PACK_SHOULDER = 0.5
# Two of the defending team's front players drop to zonal spots, (defending slot index, u, v) in
# the attackers' frame as above: the centre-forward in front of the near post, the attacking
# midfielder at the edge of the box (second balls). The wide midfielders stay up for the
# counter. Our assumption.
CORNER_ZONAL = [(10, 47.0, 5.5), (7, 37.0, 2.0)]
# Free kick near goal: the markers hold a line FREE_KICK_LINE_GAP metres goal-side of the ball
# (a few metres behind the wall, which stands 9.65 m from it), FREE_KICK_LINE[0] to [1] metres
# off the goal line (the goal area is 5.5 m deep, the penalty area 16.5 m [IFAB2025, Law 1]),
# and the six attackers stand level, 1 m upfield of them (onside), at FREE_KICK_LINE_V across.
# Our assumption.
FREE_KICK_LINE = (6.0, 18.0)
FREE_KICK_LINE_GAP = 12.0
FREE_KICK_LINE_V = (-10.0, -6.0, -2.0, 2.0, 6.0, 10.0)
# Each attacker's spot in the line is moved by up to this much (uniform, m) in depth and across,
# so the line is not ruler-straight; markers stay 1 m goal-side, so all remain onside. Our
# assumption.
FREE_KICK_LINE_JITTER = 1.0

# Clearances when a pass into the box is intercepted.
CLEAR_IN_BOX = 0.6
CLEAR_OUT = 0.45  # chance the clearance goes out of play
# A clearance goes behind for a corner only as a block or a deflection close to goal, not as a
# lob from further out: from within CLEAR_CORNER_DEPTH metres of the goal line (the goal area,
# 5.5 m [IFAB2025, Law 1]), an out clearance goes behind with CLEAR_OUT_CORNER, CLEAR_DEFLECT
# metres wider than the clearer stands (off the posts), at most CLEAR_DEFLECT_Z metres high;
# every other out clearance goes over the touchline ahead of him, for a throw-in. Our
# assumption (decision 40): before it, 40% of out clearances were aimed behind from anywhere
# in the box, up to 25 m wide (a keeper's clearance from 15 m out went over his own line).
# CLEAR_OUT_CORNER tuned to the corners per match (summary.TARGETS).
CLEAR_CORNER_DEPTH = 5.5
CLEAR_OUT_CORNER = 1.0
CLEAR_DEFLECT = (1.0, 4.0)
CLEAR_DEFLECT_Z = 1.5

# Dead-ball time before each restart, s: lognormal(median, sigma). Our assumption, tuned so the
# ball is in play about 55% of the match [Kavanagh2024, p.80; Allen2026b, Table 2].
DEAD_TIME = {
    "kick_off": (60.0, 0.15),  # after a goal
    "throw_in": (14.0, 0.3),
    "goal_kick": (23.0, 0.25),
    "corner": (32.0, 0.25),
    "free_kick": (26.0, 0.3),
}
# Opponents keep their distance until the ball is in play [IFAB2025]: 9.15 m from the ball at a
# kick-off (Law 8) and at a free kick (Law 13), 9.15 m from the corner arc at a corner (Law 17;
# the arc has a 1 m radius, Law 1), and 2 m from the point of a throw-in (Law 15). Their targets
# are kept RESTART_MARGIN further out: our assumption.
RESTART_DISTANCE = 9.15
CORNER_ARC = 1.0
THROW_IN_DISTANCE = 2.0
RESTART_MARGIN = 0.5
# A defender whose straight path would cross that circle walks round its edge instead, aiming
# this far round (rad) each frame. Our assumption.
RESTART_ARC_STEP = 0.3
# The taker stands this far behind the ball: outside the line at a throw-in or corner, away from
# the goal they attack otherwise, 0.3 m at a throw-in (roles.py). Our assumption; 1.0 m before
# decision 39, which put takers more than 1 m over the line.
TAKER_BEHIND = 0.5
# Wall: at a free kick within WALL_RANGE metres of the goal centre, the defending team lines up
# WALL_SIZE[0] players (WALL_SIZE[1] within WALL_NEAR metres) side by side, WALL_GAP metres apart,
# at RESTART_DISTANCE on the line from the ball to the goal centre. Our assumption.
WALL_RANGE = 30.0
WALL_NEAR = 22.0
WALL_SIZE = (3, 4)
WALL_GAP = 0.75  # 0.6 before decision 39 (wall players within 0.7 m of each other)
# Set-piece jobs while the ball is dead (wall players, the attackers and markers of a set piece,
# the taker) go to their spots at the pace that gets them there once SET_PIECE_DUE of the dead
# time has gone, leaving the rest to settle (``Roles.dead_pace``; at a corner, about 13 of
# 32 s): from a walk, SET_PIECE_WALK of S0 (about 2 m/s),
# up to a jog, WALL_SPEED of S0, clearly below HI_SPEED for every player (the top of S0_RANGE;
# the match tempo and the story's press apply in play only, and fatigue only slows).
# The goal huddle runs at WALL_SPEED. Our assumption (decision 40): before it every job jogged
# at 0.5 of S0 whatever the time to the restart (a corner waits about 32 s, DEAD_TIME), up to
# 5.52 m/s once decision 39 raised POSITION_EFFORT. Since decision 42 WALL_SPEED caps every job
# while the ball is dead, and a substitute's jog on, after the work rate: at most
# 0.45 × 10.3 = 4.64 m/s, whatever POSITION_EFFORT is (it had capped the work rate of CB and FB
# at 1.10, a bound the calibration, sim.calibrate, should not have).
WALL_SPEED = 0.45
SET_PIECE_WALK = 0.2
SET_PIECE_DUE = 0.4
# When the ball goes dead, a player faster than HI_SPEED brakes at BRAKE_MAX down to it (no
# sprint carried on after the whistle), then eases to his wanted speed as usual. Our
# assumption (decision 40).
DEAD_BRAKE_ABOVE = HI_SPEED
# Attackers stay at least 1 m from a wall of three or more [IFAB2025, Law 13]: their targets and
# the push keep them WALL_CLEAR from it (1 m plus a margin, our assumption).
WALL_CLEAR = 1.5
# After a goal the scorer jogs towards the nearer touchline (at most HUDDLE_RUN metres) and the
# HUDDLE_N nearest outfield team-mates gather round them, HUDDLE_RING metres away. The huddle
# holds HUDDLE_HOLD_S seconds once they have all arrived, ends at the latest HUDDLE_MAX_S after
# the goal, and at least HUDDLE_BACK_S before the kick-off can be taken (time to walk back to
# their own half). At WALL_SPEED, below HI_SPEED. Our assumption.
HUDDLE_N = 4
HUDDLE_RING = 0.85
HUDDLE_RUN = 20.0
HUDDLE_HOLD_S = 10.0
HUDDLE_MAX_S = 40.0
HUDDLE_BACK_S = 20.0
LONG_STOPPAGE = 0.10  # chance of an extra stoppage (injury, VAR, substitution) at a dead ball
LONG_STOPPAGE_S = (30.0, 90.0)

# Transitions: about 50 ± 11 per match, about 10 s each; positive 10.9 ± 3.9 s, negative
# 9.3 ± 3.4 s [Bortnik2022, Tables 1–2]. The chance that an open-play turnover starts one is
# our assumption, tuned to the count. The drawn length is longer than 10 s because many end
# early (turnover, ball out); tuned so the realised length is about 10 s (our assumption).
TRANSITION_CHANCE = 0.26  # 0.32 before decision 42 (sim.calibrate)
TRANSITION_S = (15.0, 4.5, 5.0, 27.0)  # drawn length: mean, SD, min, max
# High press: chance the defending team presses when the opponent has the ball in its own
# third; lasts at most about 10 s (high-press spells 9.8 ± 3.7 s [Bortnik2022, Table 2]).
PRESS_CHANCE = (0.25, 0.55)  # range of team styles, our assumption
PRESS_MAX_S = 10.0
