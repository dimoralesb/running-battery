"""Estimator settings (PLAN §3), with sources. "Our assumption" marks the ones we chose; those
marked "tuned" were set on default matches from seeds 1–60 (``data/synthetic/dev``), never on
the validation seeds 1001–1050 (2026-10-16).

The estimator shares the pre-processing and the CS/D′ prior with the generator, because both
are published values (synthesis §3.1, §3.2.3); it never sees the generator's hidden values.
"""

from __future__ import annotations

from secondwind.sim import params as SP

FRAME_RATE_HZ = SP.FRAME_RATE_HZ
DT = SP.DT

# --- Battery: D′ balance (PLAN §3.3, decision 2) -------------------------------------------------

# Above CS the balance drains by (v − CS) metres per second. Below CS it refills towards D′ with
# recharge time τ = k·D′/(CS − v), clipped to TAU_RANGE [Skiba2021; Jones2017, p.S76]. k = 4:
# the standard form (k = 1) refilled about 5× too fast in runners, 68 s vs 362 s fitted
# [Bellenger2025, p.721–722, Figs 2–4]. Sensitivity runs use k = 1, 3 and 5 (BUILD_PLAN §3).
K = 4.0
TAU_RANGE = (30.0, 900.0)  # s (PLAN §3.3)
# The battery refills standing still over the half-time interval, at most 15 min [IFAB2025, Law 7].
HALF_TIME_S = SP.HALF_TIME_S

# Broadcast mode: one prior for all outfield players, CS 3.7 ± 0.25 m/s clipped to 3.2–4.2 and
# D′ 180 ± 54 m clipped to 100–300 [Sutcliffe2025, Fig. 2; Liu2021, Table 4; synthesis §3.2.3]
# (the SDs as in ``sim/params.py``). Goalkeepers get the same prior (none is published for them);
# their signals are written but they are left out of tired-moment scoring.
CS_MEAN, CS_SD, CS_RANGE = SP.CS_MEAN, SP.CS_SD, SP.CS_RANGE
D_PRIME_MEAN, D_PRIME_SD, D_PRIME_RANGE = SP.D_PRIME_MEAN, SP.D_PRIME_SD, SP.D_PRIME_RANGE
# Per-player update (decision 9): about 200 draws from the prior per player.
N_DRAWS = 200
# Soft down-weighting of draws the running contradicts. A draw whose balance would go below zero
# is kept at zero by raising its D′ (the one-way correction, applied to every draw); its weight is
# exp(−½ (raise / (PENALTY_WIDTH · D′))²), so a draw that needed 10% more D′ keeps 61% of its weight
# at PENALTY_WIDTH 0.1. The width is our assumption (PLAN §3.2, "tuned in validation"): on the
# dev seeds, widths 0.05–0.4 changed the battery by less than 0.001 on average, because the
# running rarely contradicts a draw (estimated vs true D′: r = 0.03; CS: r = 0.05).
PENALTY_WIDTH = 0.10
BAND = (0.10, 0.90)  # 10–90% band (PLAN §3.2)
DRAW_SEED = 0  # draws are seeded per player id, so a player's band does not depend on the others

# --- Load: metabolic power (PLAN §3.3; synthesis §3.3) ------------------------------------------

# EC = (155.4 ES⁵ − 30.4 ES⁴ − 43.3 ES³ + 46.3 ES² + 19.5 ES + 3.6) · EM · KT, ES = a/g,
# EM = √(ES² + 1), P = EC · v [diPrampero2005, Eq. 1–4; Osgnach2010, Eq. 2–4]. KT = 1.29 on grass
# [Osgnach2010, p.173]. ES is clamped to ±0.45, the range of the polynomial [diPrampero2005]. No air
# resistance, to match Osgnach's published values (synthesis §3.3).
G = 9.81
KT = 1.29
ES_LIMIT = 0.45
EC_POLY = (155.4, -30.4, -43.3, 46.3, 19.5, 3.6)  # ES⁵ … ES⁰
LOAD_WINDOWS_S = (60, 300)  # rolling 1- and 5-min averages; never "distance above 20 W/kg"
# [Buchheit2015, Table 2: 73.6% between-trial CV]

# --- Recent intensity (PLAN §3.3; synthesis §3.4.2) -----------------------------------------------

HI_SPEED = SP.HI_SPEED  # 5.5 m/s (19.8 km/h) [Ju2022, p.974; Leifsson2024]
HSR_WINDOWS_S = (60, 120, 300)
# A "red-zone spell" (peak): a full rolling window whose high-speed distance reaches PEAK_SHARE of
# the player's reference peak for that window length. The reference is the player's own highest
# full window so far, but at least PEAK_FLOOR × the published mean peak, so the first minutes of a
# match do not count as peaks just for being the first. Published mean peaks (P1, P2, P5):
# 62, 38 and 22 m/min [Leifsson2024, Table 1; Danish league]. PEAK_SHARE about 90% (synthesis
# §3.4.2); PEAK_FLOOR 1 (our assumption): a red-zone spell needs at least 90% of the published
# mean peak. On the dev seeds the post-peak flag is then on for 16% of outfield player-seconds
# (24% with a floor of 0.75).
PUBLISHED_PEAK_M_PER_MIN = (62.0, 38.0, 22.0)
PEAK_SHARE = 0.90
PEAK_FLOOR = 1.0
# The post-peak flag stays on for about 2 min after a 1- or 2-min peak and about 5 min after a
# 5-min peak (synthesis §3.4.2; Leifsson2024, Table 1: high-speed running back to within 8% of
# the match average by minute 4 after a 5-min peak).
POST_PEAK_HOLD_S = (120, 120, 300)

# --- Tired moments (PLAN §3.3) ------------------------------------------------------------------

# A tired moment is the median battery below LOW_BATTERY of the player's estimated D′ (decided
# 2026-10-16, PLAN §7 decision 12). The post-peak flag is a separate signal with neutral wording
# ("catching breath after a red-zone spell"), never called tired. Tuned on the dev seeds against
# the short-term truth label ``tired``, outfield player-seconds: below 0.50, precision 0.30 and
# recall 0.10 (0.45: 0.34 / 0.05; 0.55: 0.26 / 0.20; 0.60: 0.22 / 0.35). The target, precision
# ≥ 0.7 at recall ≥ 0.5 (synthesis §6.3), is out of reach from positions: the same battery with
# the true CS and D′ gives 0.57 / 0.45, and with club test values 0.38 / 0.45 (20 dev seeds).
# Adding the post-peak flag (PLAN §3.3 as first written) gave 0.13–0.16 / 0.2–0.3.
LOW_BATTERY = 0.50
# Events listed with a tired spell, for the agents: the player's defensive actions (PLAN §3.3:
# duel, pressure; recovery runs are not events) and the player's own ball losses.
DEFENSIVE_EVENTS = ("duel", "tackle", "interception", "pressure", "ball_recovery", "clearance")
