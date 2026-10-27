"""Estimator settings, with sources. "Our assumption" marks the ones we chose; those
marked "tuned" were set on default matches from seeds 1–60 (``data/synthetic/dev``), never on
the validation seeds 1001–1050 (2026-10-16).

The estimator shares the pre-processing and the CS/D′ prior with the generator, because both
are published values (§3.2.3); it never sees the generator's hidden values.
"""

from __future__ import annotations

from dataclasses import dataclass

from runningbattery.sim import params as SP

FRAME_RATE_HZ = SP.FRAME_RATE_HZ
DT = SP.DT

# --- Battery: D′ balance -------------------------------------------------

# Above CS the balance drains by (v − CS) metres per second. Below CS it refills towards D′ with
# recharge time τ = k·D′/(CS − v), clipped to TAU_RANGE [Skiba2021; Jones2017, p.S76]. k = 4:
# the standard form (k = 1) refilled about 5× too fast in runners, 68 s vs 362 s fitted
# [Bellenger2025, p.721–722, Figs 2–4]. Sensitivity runs use k = 1, 3 and 5.
K = 4.0
TAU_RANGE = (30.0, 900.0)  # s
# The battery refills standing still over the half-time interval, at most 15 min [IFAB2025, Law 7].
HALF_TIME_S = SP.HALF_TIME_S


@dataclass(frozen=True)
class Prior:
    """The "typical player" of broadcast mode: one prior for all outfield players.
    Goalkeepers get the same prior (none is published for them); their signals are written but
    they are left out of tired-moment scoring."""

    cs_mean: float  # m/s
    cs_sd: float
    cs_range: tuple[float, float]
    d_prime_mean: float  # m
    d_prime_sd: float
    d_prime_range: tuple[float, float]


# "pro" (the default): a typical professional, the generator's population
# (``sim/params.py``, where the derivation is). CS 4.1 ± 0.3 m/s (14.8 km/h), clipped to 3.5–4.7:
# CS at about 85% of professionals' VO₂max [Jones2017, p.S67: 70–90%; Modric2020, Table 1]. VO₂max
# does not differ between outfield positions [Slimani2019, p.241; Modric2020, Table 1], so one
# prior for all positions. No D′ data for professionals: D′ 180 ± 54 m clipped to
# 100–300 [Sutcliffe2025, Fig. 2]. Use it for synthetic matches and for real
# tracking.
#
# "university": CS 3.7 ± 0.25 m/s (13.3 km/h) clipped to 3.2–4.2, from university players' 3-min
# all-out tests, under-16s and field-sport norms [Sutcliffe2025, Fig. 2; Liu2021, Table 4];
# the SD (range / 4) is our assumption. It sits at professionals' aerobic
# threshold, 3.38–3.98 m/s [Modric2020, Table 1], below CS by definition [Jones2017, p.S67], so
# it is kept for older or lower-level players and as a sensitivity run (and for matches generated
# before 2026-10-17, whose players were drawn from it).
#
# What the battery means with either prior: the running a typical player of that population would
# have done, not this player's own state.
PRIORS = {
    "pro": Prior(
        SP.CS_MEAN, SP.CS_SD, SP.CS_RANGE, SP.D_PRIME_MEAN, SP.D_PRIME_SD, SP.D_PRIME_RANGE
    ),
    "university": Prior(3.7, 0.25, (3.2, 4.2), SP.D_PRIME_MEAN, SP.D_PRIME_SD, SP.D_PRIME_RANGE),
}
DEFAULT_PRIOR = "pro"
# Per-player update: about 200 draws from the prior per player.
N_DRAWS = 200

# Wear (on since then): each draw's metres above its CS so far, ``W``, slow its refill,
# τ × (1 + WEAR_ALPHA · (1 − exp(−W / WEAR_SCALE_M))); half-time keeps ``WEAR_HALF_KEEP`` of W.
# The idea is the generator's tank slowing its slow pool [Chorley2022]; alpha and the scale were
# fitted on dev seeds 1–60 only (grid 0.25–2 × 400–1700 m; the lowest error within 0.001, bias
# nearest 0), then scored on held-out seeds 61–120 and the varied validation seeds. WEAR_ALPHA 0
# is the battery earlier.
# ``DRIVE`` "power" (tested earlier, not used): the battery driven by the equivalent speed,
# metabolic power over the cost of steady running on grass [diPrampero2005; Osgnach2010]. With the
# speed CS and D′ it empties every real player (IDSSE median lowest battery 5%, against a deepest
# dip of about 21% of D′ in matches [Sutcliffe2025, Fig. 3]); it would need a critical metabolic
# power, which has no published professional value.
DRIVE = "speed"
WEAR_ALPHA = 1.0
WEAR_SCALE_M = 400.0
WEAR_HALF_KEEP = 0.5
# Soft down-weighting of draws the running contradicts. A draw whose balance would go below zero
# is kept at zero by raising its D′ (the one-way correction, applied to every draw); its weight is
# exp(−½ (raise / (PENALTY_WIDTH · D′))²), so a draw that needed 10% more D′ keeps 61% of its weight
# at PENALTY_WIDTH 0.1. The width is our assumption ("tuned in validation"): on the
# dev seeds, widths 0.05–0.4 changed the battery by less than 0.001 on average, because the
# running rarely contradicts a draw (estimated vs true D′: r = 0.03; CS: r = 0.05). Re-checked
# with the professional prior (2026-10-17, dev seeds 1–60): widths 0.05–0.4 give the same battery
# to three decimals; no draw is contradicted.
PENALTY_WIDTH = 0.10
BAND = (0.10, 0.90)  # 10–90% band
DRAW_SEED = 0  # draws are seeded per player id, so a player's band does not depend on the others

# --- Load: metabolic power ------------------------------------------

# EC = (155.4 ES⁵ − 30.4 ES⁴ − 43.3 ES³ + 46.3 ES² + 19.5 ES + 3.6) · EM · KT, ES = a/g,
# EM = √(ES² + 1), P = EC · v [diPrampero2005, Eq. 1–4; Osgnach2010, Eq. 2–4]. KT = 1.29 on grass
# [Osgnach2010, p.173]. ES is clamped to ±0.45, the range of the polynomial [diPrampero2005]. No air
# resistance, to match Osgnach's published values.
G = 9.81
KT = 1.29
ES_LIMIT = 0.45
EC_POLY = (155.4, -30.4, -43.3, 46.3, 19.5, 3.6)  # ES⁵ … ES⁰
LOAD_WINDOWS_S = (60, 300)  # rolling 1- and 5-min averages; never "distance above 20 W/kg"
# [Buchheit2015, Table 2: 73.6% between-trial CV]

# --- Recent intensity -----------------------------------------------

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
# 5-min peak (Leifsson2024, Table 1: high-speed running back to within 8% of
# the match average by minute 4 after a 5-min peak).
POST_PEAK_HOLD_S = (120, 120, 300)

# --- Tired moments ------------------------------------------------------------------

# A tired moment is the median battery below LOW_BATTERY of the player's estimated D′ (decided
# 2026-10-16). The post-peak flag is a separate signal with neutral wording
# ("catching breath after a red-zone spell"), never called tired. Tuned on the dev seeds against
# the short-term truth label ``tired``, outfield player-seconds: below 0.50, precision 0.30 and
# recall 0.10 (0.45: 0.34 / 0.05; 0.55: 0.26 / 0.20; 0.60: 0.22 / 0.35). The target, precision
# ≥ 0.7 at recall ≥ 0.5, is out of reach from positions: the same battery with
# the true CS and D′ gives 0.57 / 0.45, and with club test values 0.38 / 0.45 (20 dev seeds).
# Adding the post-peak flag gave 0.13–0.16 / 0.2–0.3.
# Re-checked with the professional prior (2026-10-17, dev seeds 1–60; tired 1.3% of outfield
# player-seconds): 0.50 / 0.55 / 0.60 / 0.65 give precision 0.26 / 0.23 / 0.20 / 0.15 and recall
# 0.01 / 0.03 / 0.08 / 0.17. The same threshold sets ``low_chance``, whose
# calibration against ``tired`` is best at 0.50 (expected calibration error 0.008 / 0.008 /
# 0.014 / 0.036; it says about twice the observed share in every bin above 0.1), so 0.50 stays.
LOW_BATTERY = 0.50

# --- Typical-pro chance: calibration map ------------------------------------------

# The raw chance (the weighted share of the prior draws below LOW_BATTERY) is ordered but about
# twice too high on the dev seeds: seconds it puts at 0.1–0.2 / 0.3–0.4 / 0.6–0.7 were tired
# 10 / 18 / 38% of the time, likely because our one-pool battery refills more slowly
# than the generator's fast pool. So the engine reports a calibrated chance: the raw chance put
# through a monotone (isotonic) map from raw chance to the observed share of ``tired``, fitted on
# the default matches of dev seeds 1–60 only (never the validation seeds), and keeps the raw one
# as ``low_chance_raw``. Refitted 2026-10-27 for wear (first fitted 2026-10-17) with
# ``python -m runningbattery.validate.calibrate data/synthetic/dev``: (mean raw chance of each
# isotonic block, its share tired); in between, linear interpolation; beyond the ends, the end
# values. It holds only for the settings it was fitted with (LOW_CHANCE_MAP_FOR); with any other
# prior, k, mode, update, drive or wear the engine passes the raw chance through and says so in
# ``engine.low_chance_map``. 7,209,200 outfield player-seconds, tired 1.21%; 65% of them have a raw
# chance of exactly 0 (tired 0.1%). The knots above a raw chance of 0.7 rest on about 2,000
# seconds, so the top of the map is the least certain part.
LOW_CHANCE_MAP: tuple[tuple[float, float], ...] | None = (
    (0.000, 0.001),
    (0.021, 0.013),
    (0.071, 0.022),
    (0.122, 0.043),
    (0.173, 0.054),
    (0.222, 0.068),
    (0.273, 0.098),
    (0.324, 0.105),
    (0.374, 0.111),
    (0.423, 0.131),
    (0.521, 0.190),
    (0.671, 0.211),
    (0.766, 0.246),
)
LOW_CHANCE_MAP_FOR = {
    "mode": "broadcast",
    "update": "draws",
    "prior": "pro",
    "k": K,
    "drive": DRIVE,
    "wear": (WEAR_ALPHA, WEAR_SCALE_M, WEAR_HALF_KEEP),
}
LOW_CHANCE_MAP_SOURCE = (
    "isotonic fit on dev seeds 1–60 (pro prior, k 4, wear 1.0 / 400 m), 2026-10-27"
)

# Events listed with a tired spell, for the agents: the player's defensive actions (duel,
# pressure; recovery runs are not events) and the player's own ball losses.
DEFENSIVE_EVENTS = ("duel", "tackle", "interception", "pressure", "ball_recovery", "clearance")
