# Second Wind: Research Synthesis

What 64 papers let us build, and what they don't. (45 in the first pass; then the published Allen2024, Allen2025 and 18 more, added on 2026-10-14.)

- Per-paper notes are in [research/notes/](research/notes/). Each one has the full context, tables and page references.
- Citation keys match [READING_LIST.md](READING_LIST.md).
- Source format: `[Key, p./Table/Fig.]`. Page numbers are journal pages unless marked "PDF p.".
- "approx." means a value read off a figure.
- "derived" means our own arithmetic from published numbers, not a published value.
- Speeds are in m/s with km/h in brackets. Accelerations are in m/s².

Prepared 2026-10-14.

---

## 1. Executive summary

### What the research lets us do

1. **Model and explain temporary fatigue after intense spells.** This is the best-supported effect in the whole set.
   - After a player's most intense 5 min, high-speed running (HSR, >5.5 m/s [19.8 km/h]) is about 45% below their own match average in the next minute. It recovers over about 5 min: −45, −29, −13, −8, −4% [Leifsson2024, Table 1, p.769/772; 479 Danish players, 3 seasons].
   - After 1–2-min peaks it is back to normal within 2–3 min.
   - Sprint distance (>7 m/s [25.2 km/h]) recovers more slowly. It is still −12% at minute 5.
   - In the Premier League, the drop includes the defensive runs. Out of possession, after a peak spell players do less high-intensity **Covering** (22–44% less) and **Recovery Running** (34–43% less) than their match average [Ju2022, p.975; 50 EPL matches].
   - This is the core story of Second Wind, and it is well supported.
2. **Run a "battery" model on positions alone.** Every equation we need is published and checked against the PDFs:
   - metabolic power [Osgnach2010; diPrampero2005];
   - W′/D′ balance [Skiba2012; Jones2017], in the differential form described by its authors [Skiba2021]. Its recharge speed for **running** is uncertain: cycling lab data give τ of 32–82 s [Lievens2024], but the only running test needed τ ≈ 360 s, about 5× slower than the standard formula [Bellenger2025] (section 3.2.1b);
   - the acceleration–speed profile [Morin2021];
   - critical speed from match data [Mizelman2024];
   - the sprint motion model [Narizuka2023];
   - pitch control [Spearman2017; Spearman2018; daSilva2025].
3. **Draw a clear line between what fatigue changes and what it doesn't.**
   - Fatigue changes how much hard running a player does, and how fast and far they carry or receive the ball [Fang2024].
   - Fatigue does **not** measurably change pass completion in real matches [Fang2024; Carling2011; Rampinini2008 in-match data].
   - This gives the Verifier agent a precise rulebook (section 5).
4. **Validate honestly.** We generate the data, so we know the true fatigue. That lets us also measure something no published study controls for: how much of the "post-peak drop" is a statistical artefact of picking the maximum window (section 6.2).

### What it doesn't let us do

1. **We have no physiological player parameters from match data.**
   - Critical speed (CS) fitted from match tracking comes out at about 2.0 m/s (7.2 km/h). That is a jog, and the authors say it is "likely well below" true CS [Mizelman2024, p.2064].
   - No paper gives CS or D′ by position, or a W′ recovery time constant for running. Our defaults are informed assumptions (section 3.2).
   - The only running test of speed-based D′ balance found that with the standard recharge formula it **does not reach zero at real exhaustion** (60% of D′ left). With a recharge time fitted per runner (250–649 s, about 5× slower) it worked well (AUC 0.97) [Bellenger2025, 6 runners]. The right recharge time for football is unknown, so the battery is a relative gauge, not an exhaustion detector.
2. **Our per-position Premier League numbers are 2018/19, scaled to 2024/25.** Allen2024 (whole league, TRACAB) gives all 8 positions with SDs for 2018/19 [Table 4, p.782]. Allen2025 gives 2024/25 team totals (Second Spectrum) [Figs 2–3]. We scale the first to the second (section 4.2). That is sound for team totals, but the per-position split for 2024/25 is derived, not measured.
3. **We cannot say much about top speed and acceleration capacity.**
   - In matches, top speed barely changes from start to end: 7.65 vs 7.59 m/s, not significant [Bradley2009, p.163].
   - Laboratory sprint tests slow by only about 2–4% [SilvaJR2018, Table 5; Krustrup2006, p.1171].
   - That is smaller than the noise of an in-match acceleration–speed profile (A0 measurement error 5.4% [Morin2021, Table 1]).
   - A single match is not even enough to build a reliable profile: match-only A0 agreed poorly with a sprint test (ICC 0.23) [AlonsoCallejo2024, Table 2]; 5–6 sessions are needed.
   - So a "capacity check" cannot reliably detect fatigue within one match. The PLAN's "low energy lowers top speed and acceleration" overstates the evidence.
4. **We cannot claim fatigue causes errors.** Bad passes, bad decisions and tactical mistakes caused by fatigue are not supported in match data (section 5).
5. **Not every drop in running is fatigue.** Ball out of play, score, opponent, venue and pacing all lower running too [Bradley2013; Morgans2025; Cortez2026]. In the minute after a peak, ball-in-play time falls from 82% to 57% [Cortez2026, Table 3]. The agents must check context before saying "tired".

### The single most important caveat

Post-peak percentages depend on the baseline:

| Baseline | Drop in the next minute(s) | Sources |
|---|---|---|
| vs the player's **match average** | −25 to −48% | [Leifsson2024; Ju2022] |
| vs the **peak itself** | −77 to −97% | [Fang2024; Cortez2026] |

Only the first means "below normal". Every percentage the agents quote must say what it is compared with.

---

## 2. Metric catalogue

Column guide:
- **Track.** Computable from tracking (positions) alone? (Y / N)
- **Ev.** Computable from event data alone? (Y / N)
- **Use.** S = simulator, E = estimator, O = overlay/UI, A = agents.

**System comparability.** Values from GPS (Catapult, STATSports, WIMU), optical (TRACAB, Second Spectrum, Prozone, Amisco) and broadcast tracking are **not directly comparable**:
- Sprint distance can differ by about 50% between systems [Allen2024, p.782].
- Even two optical 25 Hz systems in the same stadiums differ: Second Spectrum reads about 10% lower HSR and about 12% lower sprint distance than TRACAB at team level [Allen2025, Fig. 1 calibration equations, derived].
- Acceleration counts differ most of all. Allen2024 did not analyse them because optical tracking measures them poorly [Allen2024, p.785].

Our reference system for targets: **optical, 25 Hz, Premier League**.

### 2.1 Volume and intensity

**Total distance (TD)**
- Definition: sum of the frame-to-frame displacement of the smoothed position.
- Unit and thresholds: m and m/min. No threshold.
- Typical values:
  - EPL 2019–21: defenders 9,966, midfielders 11,594, forwards 10,710 m [Kavanagh2024, Table 2, p.81].
  - EPL whole-match players: 112.3 m/min [Bradley 2014 via Hills2018, Table 2].
  - Serie A: 10,950 ± 1,044 m [Osgnach2010, p.174].
- Track Y; Ev. N. Use: S E O A.

**TD per ball-in-play minute**
- Definition: TD divided by effective (ball-in-play) time. Needs the ball-status field.
- Unit: m/min.
- Typical values: CSL peak 5 min 156 m/min, next 5 min 130 m/min [Fang2024, Table 2, p.98].
- Track Y (with ball status); Ev. N. Use: E A.

**High-speed running (HSR, "HSRD"/"HID")**
- Definition: distance at speed >5.5 m/s (19.8 km/h), **including** sprint. Effort minimum dwell is 0.5 s [Allen2024, p.781].
- Threshold: 5.5 m/s (19.8 km/h).
- Typical values:
  - EPL defenders 697, midfielders 992, forwards 941 m [Kavanagh2024, Table 2].
  - EPL whole-match 9.8 m/min [Bradley 2014 via Hills2018].
  - Danish league: 704 ± 258 m [Leifsson2024, p.770].
- Track Y; Ev. N. Use: S E O A.

**HSR band (Morgans' "HSR")**
- Definition: distance at 5.5–7.0 m/s only, **excluding** sprint.
- Threshold: 5.5–7.0 m/s (19.8–25.2 km/h).
- Typical values: in possession, medians CB ~0.8, FB ~2.6, CM ~1.7, W ~4.1, CF ~3.2 m/min (approx., [Morgans2025, Fig. 1, p.123]).
- Track Y; Ev. N. Use: S.

**Sprint distance**
- Definition: distance at speed >7.0 m/s. Dwell 1 s [Allen2024, p.781].
- Threshold: 7.0 m/s (25.2 km/h).
- Typical values:
  - EPL defenders 151, midfielders 158, forwards 202 m [Kavanagh2024, Table 2].
  - Danish: 308 ± 161 m [Leifsson2024]. This is a different system; see the note under 2.1.
- Track Y; Ev. N. Use: S E O A.

**Sprint count, sprint length**
- Definition: number of efforts above the threshold for at least the dwell time; length of each effort.
- Unit: n, m.
- Typical values:
  - About 35 sprints per match (>6.97 m/s, EPL 2005/06) [Bradley2009, p.162].
  - Spain: 17.3 ± 7.7 per match (>6.39 m/s [23 km/h]); CD 11.2, ED 20.0, CM 13.7, EM 22.0, F 20.7; mean length 19.3 m [DiSalvo2007, p.224].
  - **Five top leagues 2022/23 (SkillCorner broadcast, >25 km/h [6.94 m/s], ≥0.7 s, per 98 min): CD 7.2, FB 12.7, CM 8.8, WN 14.0, FW 13.2 sprints; HSR efforts (20–25 km/h) 35–61** [Castellano2025, Table 3]. PL vs LaLiga: +2.2 HSR efforts, sprint efforts no different [Table 4].
  - No EPL-only counts from optical tracking are available.
- Track Y; Ev. N. Use: S O.

**Relative sprint**
- Definition: distance above 85% of the player's own season peak speed.
- Typical values: 85% of peak speed is about 8.1 m/s (29.2 km/h); EPL distance above it 20–31 m per match [Kavanagh2024, p.80–81].
- Track Y; Ev. N. Use: E (optional).

**Recovery time between very-high-intensity (VHIR, >5.5 m/s) efforts**
- Definition: time from the end of one effort above 5.5 m/s to the start of the next.
- Unit: s.
- Typical values:
  - EPL 2005/06: CB 101, FB 74, CM 62, WM 51, A 73 s [Bradley2009, Table I].
  - It rises from 65 s in the first 15 min to 83 s in the last 15 min (+28%) [Bradley2009, p.163].
- Track Y; Ev. N. Use: S E (fatigue feature).

**Peak speed**
- Definition: maximum smoothed speed in a match (or a season).
- Unit: m/s.
- Typical values:
  - Season max, EPL: 9.53 ± 0.39 m/s (34.3 km/h). Defenders 9.63, midfielders 9.37, forwards 9.83 [Kavanagh2024, Table 1, p.80].
  - Match max, Brazil, GNSS: CD 8.09, FB 8.79, CM 8.41, WM 8.52, FW 8.29 m/s [SilvaH2025, Table 1].
- Track Y; Ev. N. Use: S E O.

### 2.2 Accelerations

**Acceleration distance (AccD)**
- Definition: distance covered while the acceleration is above 3 m/s². Decelerations are not included.
- Threshold: 3 m/s².
- Typical values: 126 ± 44 m per match, about 1.2 m/min [Leifsson2024, p.771; Prozone].
- Track Y; Ev. N. Use: S E.

**Acceleration and deceleration bands**
- Definition: distance in the bands 1–2, 2–3 and >3 m/s², for acceleration and deceleration separately.
- Typical values (Reserve League, GPS 10 Hz):
  - Acceleration >3 m/s² (HACC): 178 m.
  - Deceleration >3 m/s² (HDEC): 162 m.
  - All acceleration >1 m/s²: 1,022 m [Akenhead2013, Table 1, p.557]. This total does not equal the sum of the bands (see the note).
- Track Y; Ev. N. Use: S (GPS-scale only).

**Acceleration and deceleration counts (system-dependent)**
- Definition: number of efforts above a threshold for a minimum time. Every system uses a different rule.
- Typical values:
  - SkillCorner broadcast, ≥0.7 s, per 98 min: 1.5–3 m/s² 89–103; **>3 m/s² 5.8–9.3**; decelerations −1.5/−3 m/s² 73–91; **< −3 m/s² 13–22** [Castellano2025, Table 3]. PL has the most of the five leagues (+0.5 high accelerations vs LaLiga) [Table 4].
  - GPS STATSports 18 Hz, >3 m/s² for 0.5 s, one EPL club: **0.81–0.97 accelerations/min and 0.86–1.17 decelerations/min** (≈ 75–95 per match, derived) [Morgans2025b, Table 1].
  - ZXY radio tracking 20 Hz, >2 m/s² for 0.5 s, one Danish club: 81 accelerations and 84 decelerations per match; CD 68, wide players ~90 [VighLarsen2018].
  - **The ">3 m/s²" count differs about 10-fold between GPS and broadcast tracking.** Only within-system, relative changes are meaningful.
- Track Y; Ev. N. Use: S (shape only) E (relative change).

**Change of direction (COD) count**
- Definition: deceleration ≤ −2 m/s², a direction change ≥ 20°, then acceleration ≥ 2 m/s²; split by entry speed and angle [Deutsch2025, Methods].
- Typical values (Bundesliga 2016/17, TRACAB 25 Hz, full matches): CB 95, FB 104, **CM 107**, WM 101, ST 81, GK 51 per match; ~70% are sharp turns (120–180°); ~55% start below 3 m/s; a typical COD lasts 1.4 s [Deutsch2025, Tables 1 and 5].
- Track Y; Ev. N. Use: S O ("turns").

**Mean absolute acceleration (AveAcc)**
- Definition: mean of \|a\| across both accelerations and decelerations.
- Typical values: peak 1-min 0.94–1.07 m/s² (A-League GPS) [Thoseby2023, Table 2].
- Track Y; Ev. N. Use: S E.

### 2.3 Energetics

**Metabolic power P**
- Definition: P = EC(ES)·v, from speed and tangential acceleration (section 3.3).
- Unit: W/kg.
- Thresholds (bands): 10 / 20 / 35 / 55 W/kg [Osgnach2010, Table 3].
- Typical values:
  - Derived mean about 10.7 W/kg.
  - 26% of distance and about 42% of energy are spent above 20 W/kg [Osgnach2010, abstract and Table 3; Serie A, 25 Hz video].
- Track Y; Ev. N. Use: E O.

**Energy and equivalent distance**
- Definition: energy is ∫P dt. Equivalent distance (ED) is the energy divided by the cost of steady running on grass.
- Units: kJ/kg and m.
- Typical values: 61.12 ± 6.57 kJ/kg; ED 13,166 m; ratio ED/TD (EDI) 1.20 ± 0.03 [Osgnach2010, p.174–175].
- Track Y; Ev. N. Use: E O ("tank", fan stat).

### 2.4 Peak periods and recovery

**Peak 1/2/5-min periods (rolling)**
- Definition: the window of 1, 2 or 5 min with the most output, found separately for each variable.
- Unit: m and m/min.
- Typical values for HSR:
  - EPL players, HIR >5.5 m/s: 67 ± 19, 92 ± 28 and 113 ± 36 m for 1/3/5-min windows [Ju2022, p.975].
  - Danish: 62 / 38 / 22 m/min (P1 / P2 / P5) [Leifsson2024, Table 1].
  - Sprint (Danish): 53 / 30 / 15 m/min. AccD: 14 / 9 / 6 m/min.
- Track Y; Ev. N. Use: S E O A.

**Peak-duration curve**
- Definition: power law P(t) = c·tⁿ, with t the window length in min.
- Unit: m/min.
- Typical values (A-League GPS):
  - HSR: c = 41–59, n = −0.59 to −0.68.
  - TD: c = 177–199, n = −0.16 to −0.20 [Thoseby2023, Table 2, p.316].
- Track Y; Ev. N. Use: E (each player's "own peak" reference).

**Post-peak recovery**
- Definition: output in the 1-min bins R1…R5 after a peak, as a % of the player's match mean. The match mean excludes the peak and recovery minutes.
- Unit: % vs match mean.
- Typical values: HSR after P5: −45, −29, −13, −8, −4% (section 3.4) [Leifsson2024, abstract].
- Track Y; Ev. N. Use: S E O A.

### 2.5 Capacity

**Critical speed (CS) and D′ fitted from match data**
- Definition: CS3 or OmSD model fitted to the rolling max-mean speed for windows of 2–600 s (section 3.2).
- Units: m/s and m.
- Typical values (NCAA, 10 Hz GPS):
  - CS 2.0–2.1 ± 0.4 m/s; D′ 79–106 m. **Not physiological** [Mizelman2024, Table 3].
  - Test-based, university players: CS about 3.6 m/s, D′ 173 ± 54 m [Sutcliffe2025, Fig. 2, approx.].
- Track Y; Ev. N. Use: E (analyst view).

**D′ balance (the "battery")**
- Definition: D′ drains above CS and refills below it (section 3.2).
- Unit: m, or % of D′.
- Typical values (university players): deepest dip 21 ± 6% of D′; about 95% left at the end of the match [Sutcliffe2025, Fig. 3].
- Track Y; Ev. N. Use: E O A.

**Acceleration–speed (A–S) profile**
- Definition: a_max(v) = A0·(1 − v/S0), fitted to the top-2 accelerations in each 0.2 m/s speed bin from 3 m/s upwards.
- Units: A0 in m/s², S0 in m/s.
- Typical values (Serie A, training, 18 Hz GPS):
  - A0 7.20–7.70 ± 0.4–0.5 m/s².
  - S0 9.21–9.47 ± 0.4–0.5 m/s.
  - R² > 0.984 [Morin2021, Table 1, p.3].
- Track Y; Ev. N. Use: S (player profile), E (baseline).

### 2.6 Effect on play

**Pitch control (PPCF) with the stamina factor**
- Definition: Spearman pitch-control equation (section 3.8) with v_max,i = ξ·v95,i.
- Unit: probability (0–1).
- Defaults:
  - v95 medians: defenders about 5.08, midfielders 5.32, forwards 5.38 m/s (approx., [daSilva2025, Fig. 1]).
  - σ = 0.45 s, λ = 4.3 s⁻¹ [Spearman2017, p.7].
- Track Y; Ev. N. Use: E O A.

**Reachable area**
- Definition: after time t, a player can reach a circle with centre A·v₀ and radius B (motion model, section 4.10).
- Unit: m.
- Typical values: radius 6.16 m at 1 s and 12.94 m at 2 s (J1 League, TRACAB 25 Hz) [Narizuka2023, p.6].
- Track Y; Ev. N. Use: S (motion check), O.

### 2.7 Context and ball actions

**Contextualised high-intensity runs**
- Definition: high-intensity runs labelled by purpose: Recovery Run, Covering, Close Down, Run in Behind, Run with Ball, and others (11 classes).
- Unit: m, %.
- Typical values: in EPL peak periods, Recovery Run is 28–34% of HIR and Covering 22–25% [Ju2022, p.975].
- Track: partial (needs events and phase). Ev. N. Use: S E A.

**Transition demands**
- Definition: running per minute inside positive transitions, negative transitions, fast attacks and high presses (each about 10 s long).
- Unit: m/min.
- Typical values (Polish team, GPS 10 Hz):
  - Transition mean: TD 203, HSR 51.1, sprint 15.1 m/min.
  - 90-min average: TD 109.7, HSR 7.7, sprint 1.6 m/min [Bortnik2022, Table 3].
- Track Y (with phase labels); Ev. N. Use: S A.

**Ball-in-play (BIP) time**
- Definition: time with the ball status "alive".
- Unit: s, %.
- Typical values:
  - EPL: 45% of 95.5 min is ball out of play [Kavanagh2024, p.80].
  - After a peak minute, BIP falls from 82% to 57% [Cortez2026, Table 3].
- Track Y (ball status); Ev. Y. Use: E A (context check).

**Running per minute in and out of possession (TIP, TOOP) and the TOOP/TIP ratio**
- Definition: distance in each phase divided by the time in that phase; dead-ball time belongs to neither.
- Unit: m/min per player-slot (GK included).
- Typical values (EPL 2019/20–2023/24, Second Spectrum): **TD in possession 130–136, out of possession 142–148 m/min; HID 11.5–12.8 vs 14.8–17.6 m/min; sprint 3.0–3.3 vs 3.1–3.8 m/min** [Allen2026b, Table 5]. TD TOOP/TIP ratio 0.99–1.23 by team [Table 2].
- Overall per-minute TD is only ~106 m/min because ~43% of match time is dead ball; running during dead-ball time ≈ 63 m/min (derived from Allen2026b).
- Track Y (needs possession and ball status); Ev. N. Use: S E O A.

**Carry and receiving speed**
- Definition: speed of the ball carrier during a carry; speed of the receiver at the moment of reception.
- Unit: m/s.
- Typical values: after a peak, carry speed ES −0.32, carry length ES −0.37, receiving speed ES −0.5 [Fang2024, Fig. 1].
- Track Y (+ events); Ev. N. Use: S E A.

**Pass completion**
- Definition: completed passes divided by attempted passes.
- Unit: %.
- Typical values: no fatigue effect. CSL 80.3% → 80.5% after a peak [Fang2024, Fig. 1, approx.]. Ligue 1 midfielders 66–71% in every 15-min block [Carling2011, Table I].
- Track N; Ev. Y. Use: S A (control metric).

**Estimated effort (heart rate)**
- Definition: illustrative mapping only.
- Unit: % of maximum heart rate.
- Typical values: match mean about 85%, peak about 98%, rarely below 65% [Bangsbo2006, p.666–667].
- Track: no (it is a guess). Ev. N. Use: O (labelled "illustrative").

### 2.8 Notes on the catalogue

1. **The same name means different things in different papers.**
   - "High-intensity running" starts at 4.0 m/s (14.4 km/h) in Bradley2009, Bradley2013 and Carling2011. It starts at about 4.2 m/s in Mohr2003, at 5.0 m/s (18 km/h) in Schimpchen2020, and at 5.5 m/s in Ju2022, Leifsson2024, Fang2024 and Allen2024.
   - Morgans' "HSR" is the 5.5–7 m/s band only.
   - The Verifier must check **thresholds**, not names.
2. **Akenhead2013's acceleration table is internally inconsistent** (the band sums do not match the totals). Treat its low-band values as doubtful.
3. **Acceleration distance is not a count of accelerations.** Leifsson and Akenhead both measure distance.

---

## 3. Fatigue model specification

### 3.0 Two different models

As PLAN §2.4 asks, the simulator's hidden physiology and the estimator are deliberately different. That way the validation is not circular.

| | Simulator ("truth") | Estimator (sees positions only) |
|---|---|---|
| Short-term store | Two compartments: fast and slow (3.2.4) | One D′ balance (3.2.2) |
| Whole-match load | Slow "tank" driven by cumulative energy, with half-time partial reset and a restart dip (3.5) | Cumulative metabolic energy (3.3) |
| Effect on behaviour | Lower probability of choosing high-intensity runs; shorter, slightly slower runs; skipped covering and recovery runs (4.7) | Infers this from positions |
| Player parameters | True CS, D′, A0, S0, τ per player, with individual variation | "Test values" from metadata with ±5–10% error, plus what it can fit from the match |
| Noise | Adds position noise to the output (3.1) | Must smooth |

### 3.1 Pre-processing: from positions to speed and acceleration

**What the papers do:**
- Osgnach2010: a 187-tap FIR filter on cumulative distance at 25 Hz. The coefficients are not published.
- Morin2021: a "Gaussian-type" filter on GPS speed.
- Bou2026: Kalman filter, central differences over ±20 frames (1.64 s at 25 fps), then a 20-sample moving average on acceleration.
- Mizelman2024 removes speeds above 12 m/s; Bou2026 removes speeds above 15 m/s.

**Noise grows when you differentiate.** Speed noise is about 35σ and acceleration noise about 1,250σ at 25 Hz (σ = position error) [Osgnach2010, Eq. 9–10]. At 10 Hz this is about 14σ and 200σ (derived).

**Optical position error:**
- TRACAB vs VICON: 0.06–0.18 m for position, 0.03–0.09 m/s for velocity, 0.06–0.27 m/s² for acceleration [Bassek2025, p.7].
- Narizuka2023 assumes ±1 m for TRACAB.

- **Deutsch2025** (Bundesliga, TRACAB 25 Hz): zero-lag 4th-order Butterworth low-pass at **1 Hz** on positions, central-difference velocity and acceleration (floodlight package), then remove |a| > 10 m/s² and v > 10.5 m/s [Methods, "Data analysis"]. This is the only fully specified, published recipe for optical data in our set.

**Recommendation (our choice; Deutsch2025 gives a 25 Hz recipe, none is published for 10 Hz):**
- The simulator adds white Gaussian position noise with σ = 0.05 m per axis, plus occasional dropouts. This tests the estimator's smoothing. (Updated 2026-10-15: σ ≈ 0.1 m was the first choice. The 0.06–0.18 m above includes slow, systematic error that does not show up in speed and acceleration; 0.1 m of white noise put four acceleration bands 3–5.5 percentage points off IDSSE through our pipeline, 0.05 m keeps all within about 2. Our calibration.)
- The estimator applies a zero-phase low-pass filter to x and y, then differentiates. Default: Deutsch2025's Butterworth (4th order, zero-lag, 1 Hz cut-off) + central differences; check on IDSSE that it doesn't flatten short accelerations too much (try 1–2 Hz).
- Use **tangential** acceleration (the rate of change of speed) for metabolic power and the A–S profile. Bou2026 does not say which kind it uses; Osgnach and Morin use the speed derivative.
- Cap speed at 12 m/s and \|a\| at 10 m/s² as sanity checks.

### 3.2 D′ balance (W′ balance adapted to running)

#### 3.2.1 Equations (checked against PDFs)

**Skiba2012 integral form** [Skiba2012, Eq. 3–4, p.1528; checked against PDF images]:

$$W'_{bal}(t)=W'_0-\int_0^t W'_{exp}(u)\,e^{-(t-u)/\tau_{W'}}\,du,\qquad \tau_{W'}=546\,e^{-0.01\,D_{CP}}+316$$

- τ is in s.
- D_CP = CP − P_recovery is in **watts**, so the 0.01 constant has units of W⁻¹.
- The paper's cycling values: τ = 377 ± 29 s (recovery at 20 W), 452 ± 81 s (moderate) and 578 ± 105 s (heavy) [Skiba2012, Table 2].
- **This τ equation cannot be converted to running.** Its constants are tied to watts in 7 recreational cyclists.

**Skiba 2015 form, described in Jones2017** [Jones2017, p.S76]: the recovery time constant is the initial W′ divided by (CP − P_recovery). In that study, PCr recovered with τ ≈ 57 s and W′ with τ ≈ 334 s.

#### 3.2.1b Newer evidence on recovery (added 2026-10-14)

| Finding | Source and context | Consequence for us |
|---|---|---|
| Two forms exist. **INT** (2012) assumes some recovery always happens; **ODE** (2015) depletes above CP and recovers below CP with apparent τ = W′₀/D_CP. Neither wins on all data. The ODE form can recover too fast (τ 112 s vs 336 s fitted, Ferguson data) and predict exhaustion early | [Skiba2021, Tables 1–2, Fig. 5]; review by the model's authors | Our estimator is the ODE form. Use Skiba2021 Table 1 as a unit test |
| W′ estimates carry a typical error of **7–20%**; exhaustion doesn't happen exactly at 0 | [Skiba2021, journal p.1567] | Battery always shown with a band |
| After **partial** depletion (25% or 75%), a **one-pool** recovery is preferred by AICc. Mono τ = 32 s (25%) and 82 s (75%); about **+21–23% of W′ back in the first 30 s**, whatever the depletion | [Lievens2024]; 9 recreational men, cycling | Supports a one-pool estimator. Its fast τ is cycling; see the running row below |
| Cycling τ formulas under-predict recovery after partial depletion: Skiba-1 by 20%, Skiba-2 (τ = W′/D_CP, 234 s here) by 16%, Bartram (107 s) by 11% | [Lievens2024, Fig. 1C] | In cycling, faster τ's fit. Running points the other way [Bellenger2025] |
| After large depletion, recovery plateaus at ~83% of W′ for 10 min | [Lievens2024] | Source of residual fatigue for late-match decline |
| After **full** exhaustion, recovery has a fast part (~50%, τ ≈ 20 s) and a slow part (τ ≈ 390 s); the slow τ grows to 550–720 s after a repeat bout | [Chorley2022]; 10 trained cyclists | Two-pool truth model values (3.2.4) |
| Both τ's depend on recovery intensity: τFC 15 → 35 s and τSC ~510 → ~3,200 s from easy (50 W) to heavy (85% CP) recovery | [Chorley2023, Table 2, Eq. 6b–6c] | In the truth model, jogging near CS barely recharges the slow pool |
| **Running:** with Skiba's τ = D′/(CS − v) (68 s on average at rest), D′ balance ends at 60% of D′ in exhausting sessions (AUC 0.79; 0 sessions flagged at a 10% threshold). With **individually fitted τ of 250–649 s (mean 362 s), about 5× slower**, it ends at 7% (AUC 0.97; 75% / 100% correct) | [Bellenger2025, p.721–722, Fig. 2–4]; 6 national-level runners, GPS; exploratory | **The standard running τ is probably too fast.** Use τ = k·D′/(CS − v) with k as a parameter (section 3.2.2) |
| A three-tank hydraulic model predicts recovery ratios better than W′ balance (MAE 7.1 vs 24.9) but needs ~3 h of fitting per CP/W′ pair and 8 parameters | [Weigend2023]; cycling, published group data | Optional second truth model only |

#### 3.2.2 Our running adaptation

Swapping power for speed, CP for CS and W′ for D′ is **our adaptation**. Skiba2012 suggests the idea (p.1526, 1531) but no paper here validates it for football.

$$\frac{dD_{bal}}{dt}=\begin{cases}-(v-CS) & v>CS\\[4pt]\dfrac{(CS-v)\,(D'-D_{bal})}{D'} & v\le CS\end{cases}$$

Variables:
- v is the smoothed speed in m/s.
- CS is in m/s; D′ and D_bal are in m.
- The battery shown to users is D_bal/D′ (%).

The recovery branch is the Skiba 2015 law with τ = D′/(CS − v). Example values (derived), with D′ = 180 m and CS = 3.7 m/s:

| Recovery activity | Speed | τ |
|---|---|---|
| Standing | 0 m/s | ≈ 49 s |
| Walking | 1.5 m/s | ≈ 82 s |
| Jogging | 3.0 m/s | ≈ 257 s |

**Why this form and not Skiba2012's constants (first-pass reasoning):**
- The behavioural recovery we must reproduce is fast. HSR after a 5-min peak recovers with τ ≈ 1.6 min, i.e. about 100 s (derived from Leifsson2024's −45 → −4% over 4 min). After 1–2-min peaks it is about 0.6–0.9 min.
- Schimpchen2020 gives about 1.5–2 min (derived).
- The cycling τ of 377–578 s would predict suppression lasting 10 or more minutes. No match study shows that.

**Update after Bellenger2025 (2026-10-14): two timescales, and a correction factor k.**
- In runners, τ = D′/(CS − v) recovered about **5× too fast** (68 s vs 362 s fitted). With it, the battery barely moves; that also explains why university footballers' battery dipped only ~21% [Sutcliffe2025].
- Behaviour after a peak (minutes) and D′ refill (several minutes) need not have the same τ. Our model already separates them: the **post-peak module** (section 3.4, empirical Leifsson curves) handles the fast return of high-speed running; the **battery** is the slower capacity.
- **Recovery law for the estimator: τ = k·D′/(CS − v)**, clipped to 30–900 s.
  - k = 1 is the standard Skiba 2015 form (cycling-validated, too fast for runners).
  - k ≈ 5 matches Bellenger's running fits (≈ 360 s at rest with their D′ and CS).
  - **Recommendation: default k = 4 (between 3 and 5), sensitivity runs with k = 1, 3, 5** in validation (section 6.3). With our defaults (D′ 180 m, CS 3.7 m/s): standing ≈ 195 s, walking ≈ 330 s (derived).
- This reopens decision 2 (recharge formula): the *form* stays, the *speed* changes.

#### 3.2.3 Defaults and ranges

| Parameter | Default | Range for player variation | Basis | Strength |
|---|---|---|---|---|
| CS | 3.7 m/s (13.3 km/h) | 3.2–4.2 m/s | Field tests: university 3MT about 3.6 m/s, range 2.8–4.35 [Sutcliffe2025, Fig. 2]; U16 3.4 m/s [Liu2021, Table 4]; field-sport norms about 3.5 m/s (Kramer 2020, cited in [Liu2021]); "expected" true CS about 3.9 m/s [Mizelman2024, p.2064] | Low: no elite pro data |
| CS, professionals (added 2026-10-16) | 4.4 m/s (15.8 km/h) | 3.9–4.9 m/s | CS lies near the maximal lactate steady state, above the lactate threshold, at 70–90% of VO₂max [Jones2017, p.S67]. Professionals' anaerobic threshold: 4.29–4.57 m/s (15.5–16.5 km/h) by position, SD 0.21–0.26 m/s, at 90–93% of VO₂max; aerobic threshold 3.38–3.98 m/s [Modric2020, Table 1; 16 Croatian first-division players, 2% incline, after the off-season break]. Taking CS as that threshold speed is our assumption. VO₂max: professionals 58.2–62.2 ml/kg/min [Slimani2019, p.240], no difference between outfield positions [Slimani2019, p.241; Modric2020, Table 1] | Low–medium: one team for the speeds; no professional D′ data |
| D′ | 180 m | 100–300 m | 173 ± 54 m (range about 90–325) [Sutcliffe2025]; norms about 225 m (cited in Liu2021); traditional U16 58.8 m [Liu2021]; national-level distance runners 274 ± 54 m (CS 5.12 m/s) [Bellenger2025, Table 1]. D′ depends strongly on the method | Low |
| τ (recovery) | **k·D′/(CS − v), k = 4**, clipped to 30–900 s | k = 1–5 | Form from [Jones2017, p.S76; Skiba2021]. k ≈ 5 from running fits (τ 250–649 s at rest) [Bellenger2025]; k = 1 matches cycling lab τ of 32–82 s [Lievens2024]. Clipping is our choice | Low (conflicting; running data n = 6) |
| Smax (for fitting) | about 9.3 m/s | 8.4–10.3 | S0 [Morin2021, Table 1] | Medium |

**University vs professional prior (2026-10-16).** The university CS of 3.7 m/s sits at professionals' *aerobic* threshold (3.38–3.98 m/s [Modric2020, Table 1]), which is below CS by definition [Jones2017, p.S67], so it is likely too low for professionals. The estimator has both priors (`engine/params.py` `PRIORS`): "university" for synthetic matches, whose players are drawn from it, and "pro" for real tracking (IDSSE). The spread between professionals (SD 0.21–0.26 m/s) matches the university prior's SD of 0.25 m/s, so the limit on telling players apart (PLAN §3.3 "As built") applies to professionals too. Open question: whether the generator's players should be drawn from the professional prior (decision 11 freezes the generator for now).

**By position.** No paper gives CS or D′ by position. *(2026-10-16: Modric2020 gives anaerobic-threshold speed by position, midfielders 4.57 > defenders 4.44 > forwards 4.29 m/s, but from 16 players of one team; not used.)*
- **Recommendation: use the same prior for every outfield position.** Positional differences then come from behaviour, i.e. the role's run demands. That avoids inventing numbers.
- If we want positional flavour anyway, an **assumption** we would label as such: wide players and full-backs get D′ about +10% (more repeated sprints [Bradley2009, Table I; Morgans2025, Fig. 1]); centre-backs get CS about −0.1 m/s.

#### 3.2.4 Simulator truth: two compartments (richer than the estimator)

- Following [Skiba2012, Eq. 5; Skiba2021 "W′BAL-MULTI"], the truth model splits $W'_{exp}$ into a **fast** pool and a **slow** pool. Depletion is shared in proportion to what each pool holds [Chorley2023, Eq. 8].
- **Updated values (2026-10-14):** fast pool ~40–50% of D′, τ₁ ≈ 15–35 s; slow pool ~50–60%, τ₂ ≈ 400–500 s when walking, rising steeply when the player keeps jogging near CS [Chorley2022; Chorley2023, Eq. 6b–6c with %D_CP = (CS − v)/CS × 100]. After repeated hard efforts, τ₂ grows by 40–85% [Chorley2022]. The earlier proposal (τ₁ 60 s, τ₂ 330 s, 60/40) had a fast pool that was too slow.
- Caveat: these are cycling values after **full** exhaustion; after partial depletion the lab data don't need two pools [Lievens2024]. That is fine for a truth model (it only has to be plausible and different from the estimator), not for the estimator.
- Running check: the slow pool's τ at rest (~400–500 s) is in the range runners needed (250–649 s) [Bellenger2025]; the fast pool (~20 s) carries the quick behavioural rebound [Leifsson2024].
- Stretch goal: a second, structurally different truth model (three-tank hydraulic [Weigend2023]) to show the estimator is robust to model mismatch.
- Calibrate the split so that the simulator's **observed** post-peak HSR curve matches Leifsson2024 **after** removing the selection artefact (section 6.2).

#### 3.2.5 Getting CS and D′ in the estimator (an open choice)

| Option | How | Pro | Con |
|---|---|---|---|
| A. Fit from match data only | [Mizelman2024] method: rolling max-mean speed for 2–600 s, CS3 or OmSD fit | Purely tracking-based | CS comes out at about 2 m/s, which is non-physiological, so the battery would drain during jogging |
| B. "Club test values" in metadata | The simulator writes each player's true CS and D′ with ±5–10% error, as a club would have from a 3MT | Realistic (clubs test players); stable | Uses information beyond positions |
| C. Prior plus match update | Start from the population prior; raise D′ if the observed max-mean profile proves it must be larger | Uses data, robust | More code |

**Recommendation: B for the demo, with C as a stretch goal.** *(Superseded 2026-10-15: broadcast only, with a light version of C; see PLAN §7, decisions 1 and 9.)* Show A in analyst mode as the "match speed–duration profile", with Mizelman's warning attached. Option B is also honest: real clubs combine tests with tracking.

**What to expect.** In real matches, with test-based CS, the battery rarely empties. University players' deepest dip was 21 ± 6% of D′ [Sutcliffe2025, Fig. 3]. So the "low battery" alert must be **relative to the player's own range**, not a fixed 20%.

### 3.3 Metabolic power from speed and acceleration

Checked against PDF images. Every constant was confirmed by reproducing the band boundaries in Osgnach2010 Table 2.

**Step 1: equivalent slope and equivalent mass** [diPrampero2005, Eq. 1–4; Osgnach2010, Eq. 2–4]:

$$ES=\tan\!\left(90^\circ-\arctan\frac{g}{a_f}\right)=\frac{a_f}{g},\qquad EM=\sqrt{\frac{a_f^2}{g^2}+1}=\sqrt{ES^2+1}$$

**Step 2: energy cost and metabolic power:**

$$EC=\left(155.4\,ES^5-30.4\,ES^4-43.3\,ES^3+46.3\,ES^2+19.5\,ES+3.6\right)\cdot EM\cdot KT$$

$$P=EC\cdot v$$

Variables:
- a_f is the forward (tangential) acceleration in m/s².
- g = 9.81 m/s².
- EC is the energy cost in J·kg⁻¹·m⁻¹.
- KT = 1.29 is the grass terrain factor [Osgnach2010, p.173].
- v is speed in m/s; P is metabolic power in W/kg.

**Validity.** The polynomial is valid for ES between −0.45 and +0.45, i.e. \|a\| up to about 4.4 m/s² [diPrampero2005]. Clamp ES to this range.

**Optional air resistance.** Add k′v² to EC, with k′ ≈ 0.40 J·s²·m⁻³ per m² of body surface. That adds 0.86 J/kg/m at 9.46 m/s [diPrampero2005, Eq. 19–20]. **Leave it off by default** to match Osgnach's published values.

**Useful constants (derived):**
- At constant speed on grass, P = 4.644·v.
  - 5.5 m/s → 25.5 W/kg.
  - 7.0 m/s → 32.5 W/kg.
  - 20 W/kg needs 4.31 m/s (15.5 km/h). Osgnach itself says both 16 km/h [Eq. 17] and about 14 km/h [p.175].
- So the 35 and 55 W/kg bands are reached almost only during accelerations.

**Bands and match values (Serie A, 399 players, SICS video at 25 Hz):** [Osgnach2010, Table 3]

| Band | Time (s) | Distance (m) | Energy (kJ/kg) |
|---|---|---|---|
| Low power (LP), 0–10 W/kg | 3,818 | 4,647 | 19.01 |
| Intermediate (IP), 10–20 W/kg | 1,173 | 3,435 | 16.41 |
| High (HP), 20–35 W/kg | 461 | 1,718 | 11.89 |
| Elevated (EP), 35–55 W/kg | 163 | 670 | 6.99 |
| Maximal (MP), >55 W/kg | 91 | 451 | 6.82 |

**How to use it, per Buchheit2015:**
- Report **rolling averages** (e.g. 1-min and 5-min mean W/kg) and cumulative energy.
- Do **not** report "distance above 20 W/kg". Its between-trial coefficient of variation (CV) is 73.6% [Buchheit2015, Table 2]. In the authors' words: "practitioners should use drill average responses, not distance into zones" [Buchheit2015, p.1153].

**Limit.** Metabolic power does not see braking (eccentric) load. Decelerations look "cheap": the minimum cost is 1.75 J/kg/m at slope −0.20, before the grass factor [diPrampero2005]. That is a reason to keep a separate deceleration count in analyst mode.

### 3.4 Minute-by-minute recovery after peak periods

#### 3.4.1 Target curves

Each row has a different baseline and threshold. Use the **shape**, not mix up the sizes.

**HSR, >5.5 m/s, vs match mean excluding peak** [Leifsson2024, abstract; Table 1]

| After peak | R1 | R2 | R3 | R4 | R5 |
|---|---|---|---|---|---|
| 1-min | −29 | −6 | −3 | −2 | −2 |
| 2-min | −35 | −11 | 0 | −2 | −3 |
| 5-min | **−45** | **−29** | **−13** | **−8** | **−4** |

**Sprint, >7 m/s, same baseline** [Leifsson2024]

| After peak | R1 | R2 | R3 | R4 | R5 |
|---|---|---|---|---|---|
| 1-min | −20 | −3 | −7 | −3 | +4 |
| 2-min | −24 | −12 | −3 | 0 | −7 |
| 5-min | −39 | −29 | −18 | −17 | −12 |

**Acceleration distance (AccD, >3 m/s²) after an AccD peak, same baseline** [Leifsson2024]

| After peak | R1 | R2 | R3 | R4 | R5 |
|---|---|---|---|---|---|
| 1-min | +68 | +89 | +94 | +88 | +90 |
| 2-min | +47 | +86 | +93 | +90 | +88 |
| 5-min | +23 | +56 | +76 | +85 | +87 |

**High-intensity distance (HID, >5.0 m/s), match mean including peak, young second-tier team** [Schimpchen2020, Table 1]. Only minutes 1, 3 and 5 were analysed.

| Window | min 1 | min 3 | min 5 |
|---|---|---|---|
| 1-min | −64.4 | −4.1 (n.s.) | −30.6 |
| 5-min | −73.9 | −25.7 | −20.1 |
| 10-min | −88.9 | −42.6 | −6.1 (CI crosses 0) |

**EPL players, HIR >5.5 m/s, "next" window vs the match average for the same window length** [Ju2022, p.975]
- Next window after a 1-min peak: −48%. After a 3-min peak: −30%. After a 5-min peak: −25%. ES 0.4–0.5.

**Vs the peak itself (not "below normal")**
- CSL, next 5 min vs peak 5 min, per ball-in-play minute [Fang2024, Table 2]:
  - HIR −77.2% (ES 2.78), sprint −86.1% (ES 2.11), TD −16.6% (ES 0.57).
- World Cup, next minute vs peak minute: HSR (5.5–7 m/s) −93% (ES −5.5), sprint −97%, TD −48% [Cortez2026, Table 2].

**Older fixed-window studies**
- EPL 2005/06, HIR >4.0 m/s: peak 5 min 231 m → next 5 min 126 m, which is 6% below the other 5-min blocks [Bradley2009, Fig. 4].
- Top-class players, about 4.2 m/s: 219 → 106 m, i.e. 12% below average [Mohr2003, p.522].
- Bradley2013 finds −8% vs the match average for one 5-min block [Bradley2013, Fig. 2].

**What all these agree on:**
- The drop is largest in minute 1 and recovers within about 5 min.
- Recovery is slower after **longer** peaks and for **sprint**.
- **Total distance** recovers within about 3 min [Schimpchen2020, Table 2].
- **Intense accelerations are not suppressed** [Leifsson2024].
- Leifsson's reading: accelerations cluster in busy phases. Schimpchen's mean \|a\| is down 11–18% in minute 1, but that is a different metric and baseline.

#### 3.4.2 Model form for the estimator

The fitted time constants (derived) are:
- τ_HSR ≈ 0.6 min after P1, 0.9 min after P2 and 1.6 min after P5;
- τ_sprint ≈ 3.4 min after P5.

The estimator does **not** need to model these curves directly. They are a validation target for the D′-balance output and for the simulator's behaviour. For the overlay:
- **Post-peak flag.** Set it when a rolling HSR window exceeds about 90% of the player's own peak for that window length. Keep it on for about 2 min after a 1–2-min peak, and about 5 min after a 5-min peak.
- **Recent intensity.** Compute rolling HSR over w = 1, 2 and 5 min, divided by the player's own reference peak c·wⁿ.
  - Set c and n from the player's match so far, or use a prior: HSR n ≈ −0.63 [Thoseby2023, Table 2].
- Normalise post-peak rates **per ball-in-play minute**, as Fang2024 does. That stops stoppages from being read as fatigue.

#### 3.4.3 Choice the papers leave open: "fatigue" vs artefact

No paper controls for regression to the mean. Two mechanisms are involved:
- Picking the maximum window guarantees lower values afterwards.
- With rolling windows, the window's end also tends to sit where output is falling.

On top of that, after a peak comes a stoppage: ball in play drops from 82% to 57% [Cortez2026] and players involved from 9 to 2 [Ju2022, Fig. 1].

**Recommendation:** run Leifsson's exact pipeline on synthetic matches with fatigue **off**. Then:
- (observed curve) − (no-fatigue curve) = the fatigue part.
- Calibrate the simulator so that **observed-with-fatigue** matches Leifsson2024.
- Report both curves in the README (section 6.2).

### 3.5 End-of-match and second-half decline

**What declines, and what doesn't:**

| What | Size | Source and context |
|---|---|---|
| HIR >4.0 m/s, last vs first 15 min | −21% (466 → 374 m) | [Bradley2009, Fig. 2]; EPL 2005/06, ProZone |
| HIR (about 4.2 m/s), last vs first 15 min, top class | about −30% in the text and Fig. 3; abstract says 35–45% (internal inconsistency) | [Mohr2003, p.522–523] |
| HSR >5.5 m/s and sprint, per half | **No change**: 326 vs 336 m; 123 vs 132 m | [Bradley2009, p.162]; also [DiSalvo2007, Table 4]; [Akenhead2013, Table 1] |
| HIR >4.0 m/s, Ligue 1 midfielders, between halves | −9.3% (ES 0.6) | [Carling2011, p.66] |
| Second-half HIR (>4.0 m/s), by first-half load | −12% (ES 0.8) **only** in the high first-half activity group; moderate and low groups unchanged | [Bradley2013, p.4]; EPL 2006–09 |
| Accelerations, all bands, first vs last 15 min | −15 to −21% (ES 0.62–1.51); >3 m/s² trend only (p = 0.08) | [Akenhead2013, Fig. 1]; Reserve League, GPS 10 Hz |
| Second-half peak demands | Lower for strikers in long windows (TD 4–10 min, HSR 7–10 min) and for acceleration in STR, WD, DM (WNG long windows only); not CD or AM | [Thoseby2023, Fig. 2]; A-League GPS, 4 strikers |
| Recovery time between VHIR efforts | +28% (65 → 83 s) | [Bradley2009, p.163] |
| Top speed (mean of 5-min peaks) | 7.65 vs 7.59 m/s, not significant | [Bradley2009, p.163] |
| Sprint test (10 m) after the match | +3.5% time (ES 0.6); half-time +2.9% (only 2 effect sizes) | [SilvaJR2018, Table 5]; meta-analysis |
| Repeated sprint after intense periods | +1.6% (1st half), +3.6% (2nd half), +2.8% after the game | [Krustrup2006, p.1171]; Danish 4th division |
| Start of the 2nd half | HIR lower only in the first 10 min of each half (ES 0.3–0.4) | [Bradley2013]. Mechanism: muscle temperature falls about 2 °C at half-time [Mohr2005] |
| Per minute, 2nd vs 1st half, by role (Euro 2024) | TD/min down in most roles (ES 0.5–1.3); HIR (≥5.56 m/s)/min small, mostly ns declines (ES 0.1–0.4); sprint/min maintained | [Chen2025]; optical, full-match players, 13 roles |
| Accelerations + decelerations (>2 m/s²), 2nd vs 1st half | −11 ± 3%; HIR −6 ± 4%; TD −5 ± 1%; sprint ns. Central players declined, wide players didn't | [VighLarsen2018]; one Danish club, 8 home wins, ZXY 20 Hz |

**Mechanisms, for agent explanations** [Mohr2005; Krustrup2006]:
- **Temporary fatigue** is not explained by lactate, pH or glycogen. The leading hypothesis is potassium (K⁺) build-up in the muscle.
- **Start of the 2nd half:** the muscles cool down during half-time.
- **End of match:** about half of the muscle fibres are glycogen-empty, made worse by heat and dehydration.

**Simulator spec (our choice, calibrated to the table above):**
- A slow "tank" multiplier f_slow on the probability of choosing runs above 4 m/s.
  - It falls with cumulative metabolic energy, to about 0.80–0.85 by minute 90 for high-load players and about 0.95 for low-load players.
  - It recovers partly at half-time.
- A restart dip for the first about 5–10 min of the 2nd half.
- Maximum speed and acceleration capacity fall by **at most about 3–5%** by the end of the match.
- HSR and sprint totals per half must stay roughly flat. Fatigue shows up in **4–5.5 m/s volume, accelerations and recovery time between efforts**.

### 3.6 Capacity check with the acceleration–speed profile

**Method** [Morin2021, p.2]:
1. Keep positive accelerations only.
2. Use speeds from 3 m/s up to the player's maximum.
3. Make 0.2 m/s bins and keep the top 2 accelerations in each.
4. Fit a line, remove points outside the 95% CI, and refit.
5. Use at least 5 sessions of about 90 min.

The equation:

$$a_{max}(v)=A_0\left(1-\frac{v}{S_0}\right),\qquad \text{slope}=-A_0/S_0$$

**Limits:**
- **Measurement noise:** S0 3.3%, A0 5.4%, slope 7.6% [Morin2021, Table 1].
- **Within-match capacity loss** is about 2–5% (section 3.5).
- **Broadcast tracking is worse.** Acceleration correlation is only r = 0.716 even with heavy smoothing [Bou2026, Table 2, preprint].
- Bou2026's only fatigue example is n = 1. Its first-segment fit implies S0 ≈ 33 m/s, which is impossible.
- Rugby work cited by Bou2026 suggests at least 160 min of play for a reliable profile.
- **Match-only profiles are unreliable** even with GPS: vs a sprint test, match-only A0 ICC 0.23 (MAE 1.30 m/s²), S0 ICC 0.38; a full week (5 sessions + match) gives A0 ICC 0.51, S0 ICC 0.71. At least 5–6 sessions are needed [AlonsoCallejo2024, Table 2; Spanish reserve team, GPS 10 Hz].

**Recommendation:**
- Use the A–S profile as the player's **baseline capability**: it sets the simulator's acceleration cap, and the estimator normalises "how close to max" each effort was.
- Show a **half vs half** comparison in analyst mode only, labelled "low confidence", and only post-match (not live). Given [AlonsoCallejo2024], dropping it entirely is also reasonable.
- Do **not** use it to fire tired-moment alerts.
- A useful in-match feature is the fraction of efforts reaching ≥90% of a_max(v), compared with the player's own early-match rate (our idea; untested).

**Defaults** (Serie A, training, 18 Hz GPS) [Morin2021, Table 1]:
- A0 ~ N(7.4, 0.5) m/s², range 6.6–8.4.
- S0 ~ N(9.3, 0.45) m/s, range 8.4–10.3.

**Consistency check (derived).** S0/A0 ≈ 1.25 s. Narizuka2023 gives α ≈ 0.85 s⁻¹ (τ ≈ 1.2 s) for windows of 3–5 s [Fig. 7, approx.]. The same first-order law appears in di Prampero's sprint curve, s(t) = 10.0·(1 − e^(−t/1.42)) [diPrampero2005]. The three sources agree on a τ of about 1.2–1.4 s.

### 3.7 Showing uncertainty

**Buchheit2015** (14 French academy players, 15 years old, 4 Hz GPS, a low-speed circuit with the ball; not a match):
- During efforts, GPS metabolic power was **23 ± 10% lower** than VO₂-based power. The abstract says 29%; the Results say 23% [p.1151].
- During recovery it was **85 ± 7% lower**. Part of this is a timing mismatch: VO₂ stays high to repay the oxygen debt.
- Typical error of the estimate: 14.2% during efforts, 19.8% over the whole sequence.
- These numbers do **not** transfer directly to 25 Hz optical tracking or to Premier League running speeds.

**Recommendation:**
1. Every fatigue number in the UI is an **estimate with a band**.
2. The band width comes from **our own validation** against the hidden truth (section 6.3): the typical error and bias of battery %, and coverage. As a floor, add the parameter uncertainty: W′ (D′) estimates carry a 7–20% typical error [Skiba2021].
3. In analyst mode, add a note on metabolic power: "model-based; likely to under-estimate true energy cost (about −25% during efforts in a lab check [Buchheit2015])".
4. In fan mode, show a coarse 5-level battery icon instead of a precise %. It conveys the uncertainty without numbers.
5. Never show heart rate as data. If it is used at all, label it "illustrative effort", anchored at 65% / 85% / 98% of maximum heart rate [Bangsbo2006]. Bangsbo also notes that heart rate overstates VO₂ in matches because of heat and stress [p.667].

### 3.8 Effect on play: pitch control

**Model** [Spearman2018, Eq. 3–4; Spearman2017; checked against PDF images]. This is the Shaw / da Silva form:

$$\tau_{ij}=t_r+\frac{|r-r_i|}{v_{max,i}},\qquad f_i(t)=\frac{1}{1+e^{-(t-\tau_i)\pi/(\sqrt3\,\sigma)}},\qquad \frac{dPC_i}{dt}=\Big(1-\sum_k PC_k\Big)f_i(t)\,\lambda_i$$

Variables:
- τ_ij is the time for player i to reach point j (s); t_r is the reaction time (s).
- r is the target point and r_i the player's position (m); v_max,i is the player's maximum speed (m/s).
- f_i(t) is the probability that player i has arrived by time t; σ is the arrival-time uncertainty (s).
- PC_i is player i's control probability; λ_i is the control rate (s⁻¹).

**Defaults:**
- t_r = 0.7 s (from Shaw's code, used by [daSilva2025, p.3]).
- σ = 0.45 s and λ = 4.3 s⁻¹ [Spearman2017, p.7].
- Goalkeeper λ = 12.9 s⁻¹ [daSilva2025].
- Ball speed 15 m/s [daSilva2025].
- Defender advantage κ = 1. Keep 1.72 [Spearman2018, Table 1] as a config switch.
- Grid about 50 × 32 cells. Integrate with dt = 0.04 s to a tolerance of 0.01 (daSilva code, MIT licence).

**Stamina factor** [daSilva2025]:
- v_max,i = ξ·v95,i, where v95 is the player's 95th-percentile speed per half.
- ΔPC = λ_s·ln ξ + b, with ⟨λ_s⟩ ≈ 0.98–1.35 across teams (approx., Fig. 6b).
- **ξ is a hypothetical sweep (0.8–1.5) applied to a whole team or role group. It is not measured fatigue.**
- ΔPC units are not defined. Do not quote m² or ΔPC values.

**Realistic size of the effect:**
- Section 3.5 implies about a 3–5% loss of maximum speed. With ξ ≈ 0.96, ΔPC ≈ 1.14 × ln 0.96 ≈ −0.05 (derived, unitless).
- So the "space lost to fatigue" from reduced speed alone is **small**.
- The big spatial effect is **positional**: the player didn't make the recovery run [Ju2022]. Pitch control computed from **actual** positions captures that automatically.

**Recommendation:**
- Compute pitch control from actual positions at event moments (or at 1–2 Hz), not on every 10 Hz frame. Spearman2018 notes that one frame per event is enough.
- For the overlay, a "fresh counterfactual" (same positions, ξ = 1) can be drawn **only** as a labelled model estimate.

**Why not Fernández.** Fernandez2018's influence model is cheaper, but it has no top-speed or reaction parameter. Fatigue cannot enter it without invented rules. READING_LIST's "pick the simpler" would pick the wrong one for our purpose.

---

## 4. Simulator calibration targets

### 4.1 Reference conventions

- Speed thresholds: HSR >5.5 m/s (19.8 km/h), dwell 0.5 s. Sprint >7.0 m/s (25.2 km/h), dwell 1 s. The convention is TRACAB / Second Spectrum, EPL [Allen2024, p.781].
- Acceleration: >3 m/s² for "intense". Bands 1–2, 2–3 and >3 m/s² for analyst mode.
- Output at 10 Hz. Compute metrics after smoothing.

### 4.2 Match totals by position (per match)

**Primary source: Allen2024** (whole EPL, 2018/19, TRACAB 25 Hz, 11 v 11 games) [Allen2024, Table 4, p.782], scaled to the 2024/25 team totals in Allen2025 (Second Spectrum 25 Hz; see the team-level anchor below). Scale factors = 2024/25 team total / 2018/19 team total: **TD ×1.033, HID ×1.059, sprint ×1.163** (derived).

| Pos | 2018/19 TD (m) | 2018/19 HID > 5.5 m/s (m) | 2018/19 sprint > 7 m/s (m) | **2024/25 target TD** | **HID** | **of which HSR 5.5–7** | **sprint** |
|---|---|---|---|---|---|---|---|
| GK | 4,572 ± 591 | 31 ± 26 | 2 ± 6 | **4,720** | **33** | – | **2** |
| CB | 9,516 ± 647 | 572 ± 151 | 121 ± 63 | **9,830** | **610** | 470 | **140** |
| FB | 10,362 ± 678 | 1,008 ± 241 | 253 ± 104 | **10,710** | **1,070** | 770 | **290** |
| DM | 11,291 ± 667 | 795 ± 245 | 124 ± 80 | **11,670** | **840** | 700 | **140** |
| CM | 11,429 ± 701 | 877 ± 262 | 144 ± 91 | **11,810** | **930** | 760 | **170** |
| AM | 10,880 ± 749 | 1,053 ± 230 | 235 ± 110 | **11,240** | **1,120** | 840 | **270** |
| WM | 10,522 ± 738 | 1,127 ± 224 | 292 ± 120 | **10,870** | **1,190** | 850 | **340** |
| CF | 10,262 ± 786 | 964 ± 254 | 240 ± 120 | **10,600** | **1,020** | 740 | **280** |

How to use it:
- The 2018/19 values add up to the 2018/19 team totals (4-2-3-1: TD −0.9%, HID +0.7%, sprint +3.8%; derived). So they behave like per-position-slot values per match. The paper doesn't say whether they are full-match players only.
- The 2024/25 targets are derived; treat them as **±5% around the bold value**. The scaling is uniform across positions, but the 2014/15→2018/19 trends differed (CB and CF sprint +23–25%, CM and AM sprint unchanged [Allen2024, Table 4]). Flag this as a simplification.
- Use the 2018/19 SDs, scaled by the same factor, for the spread **between players** in a position. They are wide (CB sprint ±52%).
- Values are for a ~96.5 min match (2018/19, [Allen2024, Table 1]); the 2024/25 scaling already absorbs the longer 99.5 min matches.

**Cross-check from other sources (older or single-club).** Where these disagree with the table above, the Allen-based table wins.

| | CB | FB | CM | WM / W | FW | Sources |
|---|---|---|---|---|---|---|
| Total distance (m) | 9,900–10,600 | 10,700–11,400 | 11,400–12,000 | 11,500–12,000 | 10,300–10,700 | [Kavanagh2024, T2: Def 9,966 / Mid 11,594 / Fwd 10,710]; [Bradley2009, T I: 9,885 / 10,710 / 11,450 / 11,535 / 10,314]; [DiSalvo2007, T1, Spain: 10,627 / 11,410 / 12,027 / 11,990 / 11,254] |
| HSR >5.5 m/s incl. sprint (m) | 600–700 | 950–1,050 | 900–1,000 | 1,100–1,250 | 900–1,000 | [Kavanagh2024, T2: Def 697 (CB + FB) / Mid 992 / Fwd 941]; [Bradley2009: 603 / 984 / 927 / 1,214 / 955] |
| Sprint >7 m/s (m) | 110–155 | 240–290 | 140–205 | 300–350 | 200–265 | [Morgans2025, Figs 1–3, approx.: CB ~120 / FB ~240 / CM ~140 / W ~300 / CF ~205]; [Kavanagh2024: Def 151 / Mid 158 / Fwd 202]; [Bradley2009: 152 / 287 / 204 / 346 / 264] |
| HSR 5.5–7 m/s in possession (m/90) | ~70 | ~235 | ~155 | ~370 | ~290 | [Morgans2025, Fig. 1, approx.] |
| Sprint count | ~11 | ~20 | ~14 | ~22 | ~21 | [DiSalvo2007, p.224]; threshold >6.39 m/s (23 km/h), Spain |
| Sprint efforts >6.94 m/s, ≥0.7 s (per 98 min) | 7.2 | 12.7 | 8.8 | 14.0 | 13.2 | [Castellano2025, Table 3]; five top leagues 2022/23, SkillCorner broadcast. **Use these for count targets** |
| High decelerations < −3 m/s² (per 98 min) | 13.3 | 20.7 | 16.1 | 21.9 | 20.3 | [Castellano2025, Table 3]; same; system-dependent (section 2.2) |
| Match peak speed (m/s) | 8.1 | 8.8 | 8.4 | 8.5 | 8.3 | [SilvaH2025, T1]; Brazil, 10 Hz GNSS |
| Season peak speed (m/s) | 9.6 (Def) | 9.6 (Def) | 9.4 (Mid) | 9.4 (Mid) | 9.8 | [Kavanagh2024, T1] |
| VHIR recovery time (s) | 101 | 74 | 62 | 51 | 73 | [Bradley2009, T I] |

**Team-level anchor: current EPL, 2024/25** [Allen2025, Fig. 2 and Fig. 3 tables, Table 2; whole league, Second Spectrum 25 Hz, GK included, 11 v 11 games only]:

| Team total per match | Mean ± SD | Per player-slot per min (incl. GK) |
|---|---|---|
| Total distance | 113,891 ± 4,097 m | 104.1 ± 4.3 m/min |
| HID > 5.5 m/s (incl. sprint) | 9,611 ± 1,300 m | 8.78 ± 1.19 m/min |
| HSR 5.5–7 m/s | 7,285 ± 931 m | 6.66 ± 0.85 m/min |
| Sprint > 7 m/s | 2,326 ± 471 m | 2.13 ± 0.43 m/min |
| Match length incl. added time | 99.5 ± 2.9 min (2023/24: 101.3 ± 3.0) | |

The "/min" values are team total / (11 × match length); this is back-calculated, not stated in the paper (see Allen2025 note).

**How the cross-check table compares with Allen2024** (derived):
- HID and sprint: the cross-check ranges agree with the Allen-based targets within about 5–10% for every position.
- **TD for wide midfielders is the outlier:** the cross-check gives 11,500–12,000 m (Bradley2009, DiSalvo2007, 4-4-2-era wide midfielders), Allen2024 gives 10,522 m in 2018/19. Use Allen.
- Using the old cross-check midpoints left only about 2,200 m for the goalkeeper. Allen2024 gives GK TD 4,572 ± 591 m, which closes that gap.

**Recommendation:** use the bold 2024/25 targets, which add up to the 2024/25 team means by construction. Simulate the full 99.5 ± 2.9 min, not 90 min. Use the team SDs below as the spread between teams and the scaled position SDs as the spread between players.

**Older cross-check (EPL whole-match outfield players)** [Bradley 2014 via Hills2018, Table 2]: TD 112.3 m/min and HSR 9.8 m/min. Over about 96 min that is about 10,800 m and 940 m (derived). This agrees with Allen2025's 104 m/min per slot once the GK is averaged in.

**Context: running has grown over time.**
- EPL HID rose about 30% between 2006 and 2013 (Barnes 2014, *cited* by [Allen2024, p.780]; not Allen's own result).
- Allen2024 itself finds +12% HID and +15% sprint distance between 2014/15 and 2018/19 [Allen2024, Table 4, p.782].
- From 2015/16 to 2024/25, team HID rose 27%, sprint distance 40% and total distance only 2%. TD per minute fell 1% [Allen2025, Figs 2–3]. Part of the high-speed rise may come from the 2019/20 switch from TRACAB to Second Spectrum [Allen2025, p.1652].
- So Bradley2009 values are clearly low for today, especially for sprinting.

**Remaining gap.** No current EPL per-position **counts** (sprints, efforts, accelerations) and no in/out-of-possession split from a league-wide source (Morgans2025 is one club).

### 4.3 Peak-period values

**Peak HSR (>5.5 m/s):**
- EPL players: 67 ± 19 m (1 min), 92 ± 28 m (3 min), 113 ± 36 m (5 min) [Ju2022, p.975].
- Danish: 62 / 38 / 22 m/min for 1 / 2 / 5 min [Leifsson2024, Table 1].
- The peak 1, 2 and 5 min hold 9%, 11% and 16% of the match's HSR, in about 1%, 2% and 6% of the time [Leifsson2024, p.770].

- **By role, Euro 2024** (≥5.56 m/s, rolling 1 min): FB 69 ± 24 m, WB 74 ± 22 m, CB in a back four 51 ± 17 m; other roles 53–63 m [Chen2025, Results]. Wide defenders highest, centre-backs lowest.

**Peak sprint:** 53 / 30 / 15 m/min, i.e. 17%, 19% and 25% of match sprint [Leifsson2024].

**Peak total distance:**
- 1-min: World Cup about 190 m/min [Cortez2026, Table 2].
- A-League power law: c = 177–199 m/min, n = −0.16 to −0.20 [Thoseby2023, Table 2].

**Shape check.** EPL 1-min HSR of 67 m/min combined with n ≈ −0.63 predicts a 5-min peak of about 24 m/min. Ju2022 measured 22.6 m/min (derived). This is consistent.

**Per action.** In the peak 1 min, a recovery run averages about 42 m, against about 20 m for an average high-intensity action across the match [Ju2022, Table 2].

### 4.4 When peaks happen

**HSR peaks** are spread roughly **uniformly within each half**.
- Skewness 0–0.5, kurtosis 1.7–2.1 [Thoseby2022, Table 1]. The 1-min HSR peak starts at 22 ± 13 min into the first half.
- In 6 × 15-min periods: χ² p = .22–.38 [Schimpchen2020, Tables 3–4].

**Total distance and acceleration peaks** come **early in each half**.
- Median start 7–17 min (TD) and 6–16 min (AveAcc) [Thoseby2022, Table 1].
- 96–112 of 236 TD and Acc/Dec 5- and 10-min peaks fall in minutes 0–15 [Schimpchen2020].

**Several separate bursts, not one spell.** The 1-min HSR peak lies inside the 2-min peak only 10% of the time, and inside the 10-min peak 48% [Thoseby2022, Table 2].

**Peaks sit inside transitions** (Polish team, GPS 10 Hz) [Bortnik2022, Tables 1–3, Fig. 2]:
- 50 ± 11 transitions per game (range 32–68), each lasting about 10 s.
- Mix: 31% negative transitions, 28% positive, 26% fast attacks, 16% high presses.
- Transitions hold 51% of match sprint distance and 38% of HSR.
- Negative transitions have the highest TD (about 218 m/min) and accelerations plus decelerations. Positive transitions have the most sprinting (about 19.5 m/min) (approx., Fig. 3).

**Score.** HSR peaks don't depend on the score. Only TD and Acc/Dec peak counts fall when the margin is 2 or more goals [Schimpchen2020].

### 4.5 Size of the post-peak drop

Use section 3.4.1. **Primary target: Leifsson2024 HSR and sprint after P1, P2 and P5.** Secondary targets: Ju2022 (EPL, −48 / −30 / −25% vs match average) and Fang2024 for effort shape.

### 4.6 End of match and second half

Use the table in section 3.5. **Primary targets:**
- HIR >4.0 m/s: about −20% in the last vs first 15 min.
- HSR >5.5 m/s and sprint per half: flat (±5%).
- VHIR recovery time: +28%.
- Accelerations: −15 to −21% (first vs last 15 min) [Akenhead2013]; about −11% per half [VighLarsen2018].
- TD per minute: clearly lower in the 2nd half (ES 0.5–1.3); HIR per minute only slightly lower; sprint per minute flat [Chen2025].
- Top speed: flat.

### 4.7 How fatigue changes behaviour (effect sizes)

| Behaviour | Effect | Source and context | Simulator rule |
|---|---|---|---|
| Covering runs after a peak (players) | −22 to −44% vs match average (ES 0.2–0.3) | [Ju2022, p.975]; EPL 2018/19 | Lower the probability of starting a covering run while the fast pool is low |
| Recovery runs after a peak (players) | −34 to −43% (ES 0.2–0.3); team level −32 to −53% (ES 0.4–0.7) | [Ju2022, p.975/978] | Same rule, plus shorter runs |
| Close down / press after a peak | −27 to −45% (ES 0.1–0.2) | [Ju2022] | Lower the probability of pressing |
| Wide defenders' recovery runs | about 30–50% less in every next period | [Ju2022, p.978–981] | Position-specific weight |
| High-intensity effort shape after a peak | length −23% (19.2 → 14.8 m); duration −32% (6.3 → 4.3 s); mean speed −3% (6.33 → 6.14 m/s, ES 0.52) | [Fang2024, Table 2]; CSL 2019–21, 25 Hz, per effective minute | Shorten runs and lower cruise speed slightly. Do **not** cut top speed much |
| Carries after a peak | count −26% (ES −0.23); speed ES −0.32; length ES −0.37 | [Fang2024, Fig. 1] | Fewer, shorter, slower carries |
| Speed when receiving | ES −0.5 (11.1 → 8.9; unit not stated, probably km/h); forwards −0.57 | [Fang2024, Fig. 1] | Lower the receiver's approach speed |
| Pass completion | No change: 80.3% → 80.5% [Fang2024]; 66–71% flat across 15-min blocks [Carling2011, T I]; in-match 75% → 79% [Rampinini2008, T2, derived] | Large match studies | **No accuracy penalty** (at most ±2 percentage points of noise) |
| Pass and shot volume after a peak | Player passes −28% (CD) to −70% (CF); CF shots −74%; mostly counts during stoppages | [Cortez2026, Table 3]; World Cup | Emerges from ball-in-play falling after peaks; don't add it separately |
| Final 5 min vs first 5 min | passes 2.8 → 2.1 (ES 0.4); ball in play −12% | [Carling2011, Table II] | Emerges from ball-in-play and tempo |
| Defenders' position after a peak | Time in own third: CD 34 → 48%, FB 28 → 43% | [Cortez2026, Table 3] | Deeper line after the team's peak spells |
| Extreme peaks (within, not after) | CM ball losses 1.15 vs 0.85 per window (d 0.30); fewer long passes for FB, CM, CB | [Niu2026]; CSL 2021; Frontiers; independent t-tests | Optional, small. Low evidence |
| Lab skills (for reference only) | Pass speed −7.8% from first to last 15 min (13.3 → 12.1 m/s); shot deviation +31–38 cm within each half, recovered at half-time; dribbling unchanged | [Russell2011, Table 1, Fig. 4]; 15 youth players, simulation | Optional: small ball-speed and shot-precision penalty, reset at half-time |
| Substitutes | HIR +15% vs the same players' full matches over the same period (32.5 vs 28.3 m/min) [Bradley2013, T IV]; +27% vs whole-match players (12.4 vs 9.8 m/min) and about +10% vs the player replaced [Bradley 2014 via Hills2018]; no higher top speed; same pass completion | EPL | Subs enter with a full battery and a short "cold" ramp-up. Forwards start slowly (Carling 2010 via Hills2018) |
| Score context | CD HIR −17% when heavily winning vs heavily losing (18.0 vs 21.7 m/min); attackers +15% HIR and +54% sprint in wins | [Bradley2013, Table II] | Score-state modifiers |
| Opponent and venue | Out-of-possession HSR −0.039 m/min per league place of advantage; +0.37 m/min away (ES 0.24) | [Morgans2025, Table 1] | Context modifiers |
| Facing a top-six team (EPL 2019–24) | Possession −9 points; TOOP running/min lower (teams 7–20: HID TOOP 16.3 → 14.8 m/min, ES −0.39); ball in play +3 points | [Allen2026b, Table 5] | Weaker team sits deeper: less pressing intensity, more total running per minute |
| Team running follows the opponent | Home–away team totals correlate r = 0.68–0.75 (EPL, 9 seasons); team TD ≈ +0.71 km per km the opponent runs, +0.42 km per effective minute, −0.27 km per minute of own possession (LaLiga) | [Allen2026a, Fig. 2; Castellano2024, Eq. 1] | Generate both teams' running from shared match tempo, not independently |
| Formation | 4-5-1: about +20% HIR without the ball | [Paul2015, citing Bradley 2011] | Optional |

**Substitution timing (3-sub era)** [Myers 2012 via Hills2018, Table 1]:
- Mean entry times 57, 71 and 81 min.
- In the EPL the first sub comes at about 58 min.
- Losing teams substitute earlier.

### 4.8 Events and match flow

**Ball in play.** About 55% of time; the ball is out of play 43.1 of 95.5 min (EPL) [Kavanagh2024, p.80].
- In possession: 21.9 min (23%).
- Opponent in possession: 30.6 min (32%).
- EPL 2019–24 by team: ball in play 54–63% of match time; possession 40–64% [Allen2026b, Table 2].

**Running rate by phase (per player-slot, EPL 2019–24)** [Allen2026b, Table 5]:
- In possession ~130–136 m/min; out of possession ~142–148 m/min; dead ball ≈ 63 m/min (derived).
- HID: in possession ~12, out of possession ~15–18 m/min. Successful teams run less per minute with the ball and more without it.
- Match length 2024/25: 99.5 ± 2.9 min [Allen2025, Table 2].

**Events per match** (IDSSE, DFL, 7 matches) [Bassek2025, Table 1, p.6, Fig. 3]:
- 1,457–1,840 events of all types per match.
- About 24.4 shots per match; xG per shot 0.11 ± 0.15.
- Approx. from Fig. 3: about 740 passes, about 200 tackling duels, about 22 fouls, about 39 throw-ins and about 7.6 corners per match.

**Transitions:** 50 ± 11 per game [Bortnik2022].

**Wyscout and StatsBomb:** these Premier League event rates still need to be fitted. They are not covered by the papers read here.

### 4.9 What NOT to model

| Do not model | Why |
|---|---|
| A drop in pass accuracy with fatigue (beyond ±2 percentage points of noise) | No effect in matches [Fang2024; Carling2011; Rampinini2008 in-match]. Lab drills only [Rampinini2008 LSPT; Wang2024] |
| Decision or tactical errors caused by fatigue | Not established [Dambroz2022: 3 of 4 studies kept decision quality; tactics: one U14 small-sided-game study] |
| A large loss of top speed or acceleration (>5%) within a match | [Bradley2009] top speed flat; tests −2 to −4% [SilvaJR2018; Krustrup2006] |
| Suppressed intense accelerations after peaks | AccD is higher after peaks [Leifsson2024] |
| Absolute acceleration-count targets from the literature | Counts differ ~10-fold between systems [Castellano2025; Morgans2025b]; use our own definition and relative changes only |
| Lower shot accuracy in matches | Lab only [Russell2011]; shooting success unchanged; shots on target n.s. [Carling2011] |
| Mental fatigue | Not visible in tracking; out of scope |
| Fatigue carried over from previous matches | READING_LIST cites Julian2021, but **that paper was not downloaded or checked**. Carling2011's 3 games in 7 days (n = 7) showed no changes. Leave it out, and say the claim is unverified |
| Heart rate as ground truth | Guess on top of a guess [Bangsbo2006] |
| "Tired forwards lose the most space" | daSilva2025's role results are a hypothetical sweep, and they are small and similar for speed losses |

### 4.10 Motion model for the simulator

**Equation of motion** [Narizuka2023, Sci Rep 13:865; TRACAB 25 Hz, J1 League] (Fujimura–Sugihara model):

$$\dot{\vec v}=\alpha\,(V_{max}\,\vec n-\vec v)$$

**Reachable area** after time t is a circle:
- centre A·v₀, with A = (1 − e^(−αt))/α;
- radius B = V_max(t − A).

**Fitted values:**
- Short windows: α = 1.23 s⁻¹, V_max = 14.53 m/s (1 s); α = 1.04 s⁻¹, V_max = 11.19 m/s (2 s) [p.6].
- These imply starting accelerations of 10–18 m/s², which is not physical.
- For 3–5-s windows they settle at α ≈ 0.85 s⁻¹ and V_max ≈ 9.5–10 m/s (approx., Fig. 7).

**Recommendation (derived from several papers):**
- Per player: α = A0/S0 with V_max = S0, from the Morin defaults (τ = 1/α ≈ 1.2–1.3 s).
- Cap acceleration at a_max(v) [Morin2021].
- Add a separate braking cap of about 5–6 m/s². This is our assumption, because the model is symmetric and would allow unrealistically hard reversals at speed.
- Sprint shape from SilvaH2025:
  - the run starts from about 2.8 m/s (10 km/h);
  - the biggest gain is from −4 to −3 s, +4.25 km/h (about 1.2 m/s²);
  - braking afterwards is about −1.8 m/s² (derived);
  - speed is still 6.6–7.5 km/h at +10 s.

---

## 5. Claims register for the agents (Verifier rulebook)

**Status key:**
- ✅ **Supported**: large match studies agree.
- ⚠️ **Mixed / qualified**: allowed only with the stated qualifier.
- ❌ **Not supported**: block it.

**Global rules:**
1. Every % must name its **baseline**: "vs his match average", "vs his peak", or "vs the first 15 min".
2. Every fatigue statement uses **estimate language**: "likely", "our estimate", "the data suggest".
3. Before saying "tired" or "fatigue", the Verifier runs a **context check**:
   - Is the ball in play? (Normalise per ball-in-play minute.)
   - What is the score state? Is the team heavily ahead?
   - Did the team just lose or win the ball?
   - Is it the start of a half?
   - Was the first-half load low?
   - Is the player's role defensive?
   - Was the player just substituted on?
   If a non-fatigue explanation fits, the agent must mention it or use neutral wording ("ran less").
4. No claims about an individual's *physiology*, such as "his lactate" or "his glycogen". Only *estimates from movement*.
5. Compare phases **per minute of that phase** (in possession, out of possession, ball in play), never as raw totals: totals mostly reflect how long a team had the ball [Andrzejewski2022 vs Allen2026b].

### 5.1 Supported claims (✅)

| # | Claim pattern | Sources | Example wording the agent may use |
|---|---|---|---|
| 1 | After an intense spell, high-speed running drops for a few minutes and then recovers | [Leifsson2024; Schimpchen2020; Ju2022; Fang2024] | "After that 5-minute spell, players typically cover about 40% less high-speed distance in the next minute than their match average. It comes back over about 5 minutes." |
| 2 | Longer spells need longer recovery; sprinting recovers slowest | [Leifsson2024] | "Short bursts are shaken off in a minute or two. A five-minute spell takes about five minutes, and sprinting takes longer." |
| 3 | After a peak, players do less covering and recovery running out of possession (EPL) | [Ju2022] | "In the Premier League, players make about a third fewer high-speed recovery runs right after their most intense spell than they normally do. Our estimate says he had less in the tank for this one." |
| 4 | Transitions, especially just after losing the ball, are the most demanding moments | [Bortnik2022, single team, GPS]; [Ju2022] | "Losing the ball forces the hardest running of the game. This is where tired legs get exposed." |
| 5 | After a peak, runs get shorter; carries and receptions get slower | [Fang2024] | "His runs after that spell are shorter, and he's receiving the ball at lower speed." |
| 6 | Fresh substitutes cover more high-intensity distance per minute | [Bradley2013; Bradley 2014 via Hills2018] | "Fresh legs: substitutes typically do 15–25% more high-intensity running per minute than players who started." |
| 7 | Toward the end, players do less moderate-to-high-speed running and fewer accelerations, and need longer between efforts | [Bradley2009; Mohr2003; Akenhead2013] | "In the last 15 minutes, players typically do about a fifth less hard running than at kick-off, with longer breaks between efforts." |
| 8 | Total distance recovers faster than high-speed running | [Schimpchen2020; Leifsson2024] | "He's still moving, but the high-speed runs aren't there yet." |
| 9 | Temporary fatigue is not caused by lactic acid | [Krustrup2006; Mohr2005] | "It isn't 'lactic acid'. Scientists think it's a short-lived disturbance in the muscle's salt balance, which clears in minutes." |
| 9a | Both teams' running rises and falls together | [Allen2026a, r = 0.68–0.75; Castellano2024] | "When one side raises the tempo, the other has to match it: in the Premier League the two teams' running totals move closely together." |
| 9b | Teams run harder per minute without the ball than with it | [Allen2026b, Table 5] | "Without the ball, Premier League players typically cover about 10% more ground per minute than when they have it." |
| 9c | Recovery starts fast: a good part of short-term capacity comes back within the first 30 s | [Lievens2024; Chorley2022]; lab, cycling | Analyst mode: "In lab tests, about a fifth of the short-term reserve returns in the first 30 seconds of easy recovery." |

### 5.2 Mixed or qualified claims (⚠️)

| # | Claim pattern | Sources | Required qualifier / example |
|---|---|---|---|
| 10 | "He's slower now" (top speed) | [Bradley2009] flat in matches; [SilvaJR2018] −3.5% in tests | Only for **repeated** efforts or after a peak: "His last few sprints were a bit slower than earlier ones." Never "he's lost his pace". |
| 11 | "His battery is low" / D′ balance | Model adapted from cycling [Skiba2012; Jones2017]; parameters are assumptions | "Our model estimates his short-term energy is low", with the uncertainty band. |
| 12 | "He's covered X km, like running Y km" (equivalent distance) | [Osgnach2010]; [Buchheit2015] underestimate | "About X km, an effort roughly like Y km of steady running (model estimate)." |
| 13 | Drop in running due to fatigue vs tactics | [Bradley2013; Morgans2025; Cortez2026] | Must pass the context check. "His running dropped while his team sat on a 3–0 lead, so this may be tactical rather than fatigue." |
| 14 | Pass, shot or touch **volume** falls after peaks or late | [Cortez2026; Carling2011] | Only together with ball-in-play: "Fewer touches, partly because the ball was out of play more." |
| 15 | Second-half drop | [Bradley2013]: only high first-half load; [Thoseby2023]: acceleration peaks | "Players who ran hardest before the break usually do a bit less after it." |
| 16 | Kicking / pass **speed** and shot precision drop | Lab only [Russell2011]; youth players | Analyst mode only: "In lab tests, tired players strike the ball a little slower and less precisely." Never applied to a specific pass. |
| 17 | "Space lost because he's tired" (pitch control) | [daSilva2025] model; hypothetical ξ | "Model view: if he were fresh, we estimate he'd control a bit more of this area." Show the map; no m². |
| 18 | Extreme spells → central midfielders lose the ball more | [Niu2026]; d 0.30, independent t-tests, Frontiers | Analyst mode only, as "a weak association in one league". |
| 19 | Acceleration–speed profile shows fatigue | [Bou2026] preprint, n = 1; [Morin2021] noise 5%; match-only profile ICC 0.23 [AlonsoCallejo2024] | Analyst mode, post-match, half vs half, "low confidence". No fan claims. |
| 19a | "Teams that sprint more finish higher" | rs = .32 (2015–24) [Allen2026a]; r = .25 (2019–24) [Allen2026b]; small | "Higher-placed teams tend to sprint a little more; it's a weak link, not a recipe." |
| 19b | "Pressing harder (out-of-possession running per minute) goes with success" | r = .34–.45; TOOP/TIP ratio r = .50–.65 [Allen2026b] | Association only: "Successful teams tend to work harder without the ball than with it." Never "they won because they pressed more". |
| 19c | "His battery is empty" / "he's exhausted" | With the standard τ, speed-based D′ balance stayed at 60% at real exhaustion; it only worked with τ fitted per runner [Bellenger2025]; football τ unknown; W′ error 7–20% [Skiba2021] | Only relative: "lowest point of his match", "lower than his teammates". |

### 5.3 Not supported (❌): block

| # | Claim pattern | Why | Allowed alternative |
|---|---|---|---|
| 20 | "Misplaced the pass because he was tired" | Pass completion unchanged in matches [Fang2024; Carling2011; Rampinini2008] | "He'd just finished a hard spell. In general, passing accuracy holds up under fatigue." |
| 21 | "Bad decision / lost concentration because tired" | [Dambroz2022]: not established; mental fatigue isn't visible in tracking | None. Describe the action only. |
| 22 | "Missed the shot because tired" | Shooting success unchanged [Russell2011; Carling2011] | None |
| 23 | "He can't accelerate any more" right after a peak | AccD is higher after peaks [Leifsson2024] | "He's still making short bursts, but fewer long high-speed runs." |
| 24 | Any % without a baseline, or "−93% / −77%" presented as "below normal" | These are vs the peak [Cortez2026; Fang2024] | Use match-average figures (Leifsson, Ju) |
| 25 | "His lactic acid / lactate is high" | Doesn't track temporary fatigue [Krustrup2006] | Claim 9 wording |
| 26 | "Tired from Wednesday's match" | Not modelled; source unverified (Julian2021 not checked) | None |
| 27 | Heart-rate claims ("his heart rate is 180") | No heart-rate data | Illustrative effort only, labelled |
| 28 | "Tired forwards lose the most space" | daSilva2025 role effects for speed losses are small and similar | None |
| 29 | Exact numbers for one player's physiology ("CS 3.8 m/s") presented as measured | Parameters are assumptions or test-like metadata | Analyst mode: "model parameter (assumed)" |
| 30 | "They won because they ran more" / "outran them, so they won" | Winners outrun losers only trivially to slightly (TD +0.7%, ES 0.22; sprint +5%, ES 0.29) [Allen2026a, Table 3]; total distance unrelated to points in 2019–24 (r = .04) [Allen2026b]; technical variables dominate [Andrzejewski2022] | "Both teams ran a similar amount; the difference was in what they did with it." |
| 31 | "They ran more with the ball, so they played better" | In-possession running per minute correlates **negatively** with points (TD TIP r = −.57) [Allen2026b] | None |
| 32 | Comparing a player's acceleration count with a published number | Counts depend on the tracking system (~10-fold) [Castellano2025; Morgans2025b] | Compare only with his own earlier periods |

---

## 6. Validation plan

### 6.1 Realism of synthetic matches

The acceptance thresholds are **our proposals**.

| Check | Target | Pass if |
|---|---|---|
| Totals per position | Section 4.2 ranges | Mean of each position within the range; between-player SD 5–10% for TD and 25–35% for HSR. SD reference: HSR SD of 258 m on a mean of 704 m [Leifsson2024]; match-to-match coefficient of variation 9.2% [Mohr2003] |
| Speed and acceleration distributions | IDSSE (TRACAB 25 Hz, resampled to 10 Hz) | Speed-band time shares within ±3 percentage points. Reference: walking 68.3% of time; >22 km/h (6.1 m/s) 1.3% [Osgnach2010, Table 1]. \|a\| >3 m/s² about 0.9% of time each way [Osgnach2010, Table 2] |
| Ball in play | 55% [Kavanagh2024]; 54–63% by team [Allen2026b] | 50–63% |
| Running by phase | In possession ~133, out of possession ~145, dead ball ~63 m/min per player-slot [Allen2026b, derived] | Each within ±10%; out-of-possession > in-possession for most teams |
| Two teams move together | Home–away team TD/HID/sprint r = 0.68–0.75 [Allen2026a, Fig. 2] | r between 0.5 and 0.85 over ≥ 50 synthetic matches |
| Effort counts | Sprint efforts per position [Castellano2025, Table 3] | Within ±30% (system difference) |
| Events per match | [Bassek2025]; Wyscout EPL | Passes, shots and duels within ±15% |
| Peak-duration curve | HSR exponent n ≈ −0.6; TD n ≈ −0.18 [Thoseby2023] | n within ±0.1; 1-min HSR peak 50–85 m [Ju2022] |
| Peak timing | HSR uniform within halves; TD and acceleration peaks early [Thoseby2022] | HSR peak start times: KS test p > 0.05 against uniform. TD peak start median < 15 min into each half |
| Self-containment | 1-min HSR peak inside the 2-min peak about 10% of the time [Thoseby2022, Table 2] | < 30% |
| Post-peak curves | Section 3.4.1, Leifsson P1/P2/P5 | Every R1–R5 value within ±10 percentage points; minute-1 drop after P5 between −35 and −55% |
| Acceleration after peaks | Not suppressed [Leifsson2024] | AccD over R1–R5 ≥ match mean |
| End of match | Section 3.5 | HIR >4 m/s in the last 15 min 10–30% below the first 15; HSR and sprint per half within ±10%; VHIR recovery time up 15–40% |
| Transitions | 50 ± 11 per game, about 10 s each [Bortnik2022] | 35–65 per game |
| Motion model | Reachable area circular for v₀ ≤ 6 m/s [Narizuka2023] | Fitted α and V_max stable across windows (no tracking noise in the truth) |
| A–S profile recovery | Morin method on synthetic data returns the true A0 and S0 | Error < 5% with ≥ 1 match of data |
| Context effects | Score, venue and opponent modifiers (section 4.7) | Signs correct; sizes within 2× |

### 6.2 Selection-artefact control (the "placebo match")

1. Generate N matches with fatigue **off**: same tactics and seeds, no fatigue in the hidden physiology.
2. Run the exact Leifsson2024 and Ju2022 pipelines on them.
3. The post-peak "drop" that remains comes from window selection and the flow of play.
4. Report three curves side by side: published, synthetic-with-fatigue, synthetic-without-fatigue.

This is a methods contribution no published paper makes. It is the strongest rigour slide for the judges.

### 6.3 Estimator vs hidden truth

**Signals compared:**
- estimated battery (D_bal/D′) vs true fast-pool and combined state;
- estimated "tank" vs the true slow component;
- "tired moment" flags vs true low-capacity moments.

**Metrics:**
- Pearson and Spearman correlation per player-match.
- Mean absolute error (MAE) and bias of battery %.
- **Coverage** of the uncertainty band: target 80% of truth inside an 80% band.
- Precision and recall of tired-moment detection: target precision ≥ 0.7 at recall ≥ 0.5 (our proposal).

**Robustness:**
- position noise σ = 0.05, 0.1, 0.3 and 1.0 m;
- 10 Hz vs 25 Hz;
- dropouts;
- ±10% error in the CS and D′ "test values";
- broadcast-like partial visibility (SkillCorner-style), as a stretch goal.

**Confounder test cases.** These are scenarios where the agent must **not** say "tired":
- the team leads 3–0 and sits back;
- a long stoppage;
- the start of the 2nd half;
- a low-load player's late drop.

**Avoiding circularity.**
- The truth uses two compartments, individual τ, behavioural decisions and the slow tank.
- The estimator uses one compartment and positions only.
- Also report how the estimator degrades when truth parameters are drawn from wider distributions.

### 6.4 Agent and Verifier tests

- A suite of about 50 generated narrative sentences, half valid and half from section 5.3.
- The Verifier must block every one in 5.3, and every % with no baseline.
- Measure the false-block rate on supported claims.

---

## 7. Data requirements for the generator

### 7.1 Tracking (`tracking.jsonl`, 10 Hz)

**Per frame:**
- `frame`, `t` (s since kick-off), `period` (1/2), match clock;
- `ball_status` (alive/dead): needed for effective-time normalisation [Fang2024] and context checks;
- `possession_team`;
- ball `x, y, z`.

**Per player:**
- `player_id`, `x`, `y` (m).
- Optional `vx`, `vy`, but the estimator must recompute speeds from positions. IDSSE's provided speed field lags [Bassek2025, Box 3].

**Coordinates:**
- Centre origin, metres, a 105 × 68 m pitch, attacking direction known per period.
- Note: in IDSSE, positions use a centre origin but events use a corner origin [Bassek2025, Boxes 2–3]. Write a converter.

**Noise:** add realistic position noise (section 3.1). Keep a noise-free copy for debugging only.

### 7.2 Events (`events.jsonl`, SPADL / StatsBomb-like)

**Fields:**
- `id`, `t`, `period`, `type`, `subtype`, `player_id`, `team_id`;
- `start_xy`, `end_xy`, `outcome`, `body_part`;
- `possession_id`, `phase` (build-up / progression / final third / positive transition / negative transition / high press / set piece);
- `score_state`.

**Types needed by the metrics:**
- pass (with length, height and outcome);
- **carry**, with start and end, so carry speed and length can be computed [Fang2024];
- **reception**, so receiving speed can be computed [Fang2024];
- shot (with xG);
- duel (won/lost), tackle, interception, pressure, ball recovery, ball loss;
- foul, ball out, throw-in, corner, free kick, goal kick;
- substitution, goal, cards.

### 7.3 Metadata (`metadata.json`)

- Pitch size; teams (fictional names); line-ups; formation; positions.
  - Position codes: CB, FB, DM, CM, AM, WM/W, CF. Allen2024 uses GK, CB, FB, DM, CM, AM, WM, CF.
- Substitutions.
- Per-player "club test values": CS, D′, A0, S0, with measurement error vs truth (section 3.2.5).
- Fictional player names.

### 7.4 Truth (`truth.json`, per player per second; validation only)

- Fast-pool, slow-pool and tank states.
- Effective capacity multipliers: speed, acceleration, run-choice probability.
- Labels for **intended run type** (Recovery Run, Covering, Close Down…, following Ju2022's 11 categories). This lets us check the estimator's run classification too.
- Labels for skipped runs: the run a fresh player would have made.
- True tired-moment labels.

### 7.5 What changes in the data strategy (PLAN §2.2)

**IDSSE / Bassek2025:**
- Only 7 matches from 2022/23: 2 Bundesliga (both matchday 34) and 5 2. Bundesliga, all Fortuna Düsseldorf home games.
- TRACAB Gen5 at 25 Hz; DFL XML format.
- Access via figshare (doi:10.6084/m9.figshare.28196177) and the **floodlight** Python package (`io.dfl`, `io.datasets`). The paper does not mention kloppy; check whether kloppy's Sportec/DFL loader reads it.
- Events are **not synchronised** in the release. The raw offset is −0.37 ± 1.82 s (max 27 s) [Bassek2025, p.8].
- **Use it for speed and acceleration distributions and to test our pipeline, not for "fatigue patterns over 90 min".** Seven matches is too few, and the set is skewed.

**Allen2024 / Allen2025:** both now read (published versions). Together they give the per-position shape (2018/19) and the current team totals (2024/25); see section 4.2.

**Sutcliffe2025:** raw data are on Harvard Dataverse (licence not checked). This is a possible source of real CS, D′ and match-GPS data for checking D′ balance.

**Pitch control reference code:** github.com/Markfds01/Tracking_laliga (MIT) [daSilva2025]. Check the licence before reusing any code.

**Possible follow-up reading** (not read here):
- Skiba & Clarke 2021 and Kirby 2021 (D′ balance in running).
- Trewin et al. 2017 (context factors review).
- Julian2021 (needed to support "no carry-over").

---

## 8. Contradictions and gaps

### 8.1 Contradictions between papers

| Topic | Disagreement | How we handle it |
|---|---|---|
| Size of the post-peak drop | −29 to −45% [Leifsson2024] vs −64 to −89% [Schimpchen2020] vs −77 to −97% [Fang2024; Cortez2026] | Different thresholds (5.5 vs 5.0 m/s) and baselines (peak excluded, peak included, the peak itself). Use Leifsson as the primary target; always state the baseline |
| Accelerations after a peak | Up +23 to +94% [Leifsson2024, AccD >3 m/s²] vs mean \|a\| down 11–18% in minute 1 [Schimpchen2020] | Different metrics. Model: intense accelerations not suppressed; total movement briefly lower |
| End-of-match decline | Abstract says 35–45% [Mohr2003] vs about 30% in its own text and figure; HSR >5.5 m/s flat between halves [Bradley2009; DiSalvo2007; Akenhead2013] | The decline is in moderate-speed volume and accelerations, not half totals of HSR |
| Top speed with fatigue | PLAN says it drops; matches show it flat [Bradley2009]; tests show −2 to −4% [SilvaJR2018; Krustrup2006] | Small capacity effect; the main effect is behavioural |
| Match-fitted vs test CS | about 2.0 m/s [Mizelman2024] vs 3.4–4.1 m/s [Sutcliffe2025; Liu2021]. Fits Jones2017: intermittent work lowers CP and raises W′ | Use test-like values (section 3.2.5) |
| W′ recovery τ | Cycling 2012 constants 377–578 s [Skiba2012]; cycling lab after partial depletion 32–82 s [Lievens2024]; behavioural rebound 0.6–3.4 min [Leifsson2024, derived]; **running field fits 250–649 s, about 5× slower than τ = D′/(CS − v)** [Bellenger2025] | Two timescales: fast rebound in the post-peak module (3.4), slower battery with τ = k·D′/(CS − v), k = 4, tested at k = 1–5 (3.2.2) |
| One or two recovery components | Two (fast + slow) after full exhaustion [Chorley2022; Chorley2023; Caen via Lievens2024] vs one after partial depletion [Lievens2024] | One pool in the estimator; two pools in the simulator truth |
| Does running relate to winning? | Small positive links in EPL 2015–24 [Allen2026a] vs only sprint (r .25) in 2019–24 [Allen2026b]; technical variables dominate in the Bundesliga [Andrzejewski2022] | Treat running–success links as weak and fading; block causal claims |
| Out-of-possession running and success | Totals without the ball correlate **negatively** with points [Andrzejewski2022] vs per-minute out-of-possession running correlates **positively** [Allen2026b] | Not a real conflict: totals reflect possession time. Always use per-minute rates per phase |
| Acceleration counts | ~75–95 per match >3 m/s² (GPS) [Morgans2025b] vs 6–9 (broadcast, ≥0.7 s) [Castellano2025] vs 81 >2 m/s² (ZXY) [VighLarsen2018] | System and rule dependent; relative use only |
| Lab vs match passing | LSPT penalties +62% after the 2nd half, but in-match pass success unchanged, **in the same study** [Rampinini2008] | Matches win: no accuracy penalty |
| Simulation vs matches | Neuromuscular test losses are larger after simulations than after real 11 vs 11 matches (CMJ −0.65 / −1.13 vs −0.15) [SilvaJR2018, Fig. 4] | Players pace themselves in real matches; prefer match evidence |
| Which substitutes gain | Central midfielders [Bradley2013] vs attackers [Bradley 2014 via Hills2018] | Model a general +10–25% HIR; don't claim a position effect |
| Pitch-control parameters | σ 0.45 vs 0.54 s; λ 4.30 vs 3.99 s⁻¹; κ only in 2018 [Spearman2017 vs Spearman2018]; daSilva text 10 s integration vs code 50 s | Use the 2017 values (the da Silva baseline), κ = 1 |
| Within-paper errors | Dambroz2022 misreports Russell's pass accuracy; Wang2024 overstates; Cortez2026 abstract vs results; Thoseby2023 position lists inconsistent; Kavanagh2024 30% ASR threshold inconsistent with its formula; Osgnach2010 16 vs 14 km/h; Buchheit2015 29 vs 23%; Russell2011 shot-speed text vs figure; SilvaJR2018 "recovered by 72 h" vs −4.8% peak speed | Notes flag each one; we use the tables over the abstracts |

### 8.2 Gaps in the evidence

1. **No elite CS or D′, no positional CS or D′, and no running τ.** These are assumptions; we test their sensitivity in validation.
2. **The 2024/25 per-position split is derived, not measured** (Allen2024 2018/19 positions scaled to Allen2025 2024/25 team totals). Recent effort **counts** now exist for the five top leagues pooled [Castellano2025, broadcast tracking], but not EPL-only from optical tracking. Per-half data now exist for Euro 2024 [Chen2025]; 15-min-period EPL data are still from 2005/06.
3. **No post-peak recovery by position, score or individual.** Leifsson2024 is pooled. We also have no recovery curve beyond 5 min, and no acceleration data after peaks except Leifsson.
4. **No study controls for regression to the mean.** Our placebo-match method fills this (6.2).
5. **No acceleration data from optical tracking** at league level [Allen2024].
6. **No validation that D′ balance or A–S profiles track within-match fatigue** [Sutcliffe2025; Bou2026]. The one running validation of speed-based D′ balance worked only after fitting a much slower τ per runner [Bellenger2025, 6 runners], and match-only A–S profiles are unreliable [AlonsoCallejo2024]. Apart from Bellenger, all recovery-kinetics data are from cycling. **No football-specific τ exists.**
7. **No real-match link from fatigue to pass quality under pressure**, and no data on the first 2 minutes after a peak for skills.
8. **No 5-substitute-era substitute data** [Hills2018 is the 3-sub era].
9. **Context effects are poorly quantified.** Only Morgans2025 (opponent, venue) and Bradley2013 (score) give numbers; Paul2015 is a commentary with no data.
10. **Several sampling rates are unknown**: Prozone in Leifsson2024 and Bradley2013; Ju2022's system. That limits how comparable they are.

### 8.3 Corrections to READING_LIST.md and PLAN.md found while reading

| Where | Says | Actually |
|---|---|---|
| READING_LIST, line 13 | Allen2024 shows about +30% HSR 2006→2013 | That is Barnes 2014, cited by Allen. Allen's own result: +12% HSR, +15% sprint from 2014/15 to 2018/19 |
| READING_LIST, Leifsson2024 | "Recovers over ~5 min"; "accelerations go up after the peak" | About 5 min only after 5-min peaks (2–3 min after 1–2-min peaks). Sprint is still −12% at minute 5. AccD is higher after **AccD** peaks; accelerations cluster in busy phases |
| READING_LIST, Schimpchen2020 | Benfica, full season; "still 6–31% lower at min 5" | A young **second-tier** Portuguese team, ≥5.0 m/s (18 km/h), 10 Hz GPS. The 6% is not significant |
| READING_LIST, Mizelman2024 | "Our default player parameters" | The authors say match-fitted CS (about 2 m/s) is not physiological |
| READING_LIST, Morin2021 | "From normal tracking data" | Training GPS, ≥5 sessions; matches were not tested |
| READING_LIST, Ju2022; PLAN line 91 | "Players do 20–53% less" | 20–53% is the combined player/team range in the abstract. Players: Covering −22 to −44%, Recovery Run −34 to −43%. Teams: −20 to −41% and −32 to −53%. All vs match average |
| READING_LIST, Cortez2026 | "HSR drops 93%; all technical variables drop" | −93% is vs the **peak minute**. Technical variables are **counts only** (fewer actions, not worse), confounded by ball in play falling from 82% to 57% |
| READING_LIST, Fang2024 | Fine | Add: changes are vs the peak 5 min, per effective (ball-in-play) minute |
| READING_LIST, Niu2026 | "CB improve short-pass accuracy" | Wrong: these are counts of successful passes; no accuracy was tested. It compares **during** extreme vs ordinary peaks, not after a peak |
| READING_LIST, Bortnik2022 | "Negative transition has the highest running demand" | Only for total distance and accelerations plus decelerations; positive transitions have the most sprinting. One Polish team, GPS. The DOI printed in the PDF is 10.5114/biolsport.2023.112968 |
| READING_LIST, SilvaH2025 | "Speed drop after a max sprint" (fatigue) | It is the braking within the same run, not fatigue. Last author (Marcelino) missing from the citation |
| READING_LIST, daSilva2025 | "How the stamina factor lowers top speed" | The stamina factor is a hypothetical multiplier, not measured fatigue |
| READING_LIST, Spearman2017 | Reaction time, top speed and acceleration parameters | Only σ and λ are fitted. 5 m/s and 7 m/s² come from Spearman2018; 0.7 s reaction time from Shaw's code |
| READING_LIST, Fernandez2018 | "Pick the simpler" | The simpler model has no speed parameter for fatigue to act on |
| READING_LIST, Buchheit2015 | "~29% during efforts" | The abstract says 29%; the Results say 23 ± 10%. Youth players, 4 Hz GPS, low-speed circuit |
| READING_LIST, Bangsbo2006 | Energy demands | No match energy expenditure, activity-change counts or sprint counts; heart rate, %VO₂max and metabolites only |
| READING_LIST, Wang2024 | "Significantly worsen short passing" | Overstated: vote counting; mixed and non-significant results |
| READING_LIST, Sutcliffe2025 | "D′bal method details" | τ and the D′bal equation are not reported |
| READING_LIST, Akenhead2013 | Premier League | Premier **Reserve** League (mean age 19.3 y), GPS 10 Hz, acceleration *distance* |
| READING_LIST, DiSalvo2007 | Implicitly EPL | Spanish league + Champions League, Amisco 25 Hz |
| READING_LIST, Kavanagh2024 / Morgans2025 | Premier League | **One club each** (16 / 31 players), Second Spectrum 25 Hz. Morgans gives no total distance |
| READING_LIST, Narizuka2023 | arXiv preprint | Published: Sci Rep 13:865 (2023), doi:10.1038/s41598-023-27999-1 |
| READING_LIST, Julian2021 | "So we don't model carry-over" | Not downloaded, so the claim is unverified |
| PLAN, line 50 | "Low energy lowers top speed and acceleration [Ju2022, daSilva2025, Akenhead2013]" | None of these measured capacity. Akenhead = acceleration volume; daSilva = hypothetical. The supported version is "fewer and shorter hard runs, slightly slower; skipped covering and recovery runs" |
| PLAN, §2.2 | IDSSE for "fatigue patterns over 90 min" | 7 skewed matches: use it for distributions |

---

## 9. New ideas

### 9.1 Story moments for the live overlay

1. **"Red zone" spell.** A player's rolling 1–2 min HSR passes about 90% of their own peak. The overlay pulses their battery.
2. **"Exposed on the turnover."** The team loses the ball (negative transition) while a defender is in a post-peak window. Show the gap they didn't close, alongside the recovery-run statistic [Ju2022; Bortnik2022].
3. **"Second wind."** The moment a player's high-speed output is back to their normal level after a spell, about 2–5 min later [Leifsson2024]. This literally names the project, and it gives a positive story too.
4. **"Fresh legs."** Substitute impact: the sub's HIR per minute vs the player they replaced and vs the team [Bradley2013; Hills2018].
5. **"The legs drop, the passing doesn't."** Analyst chart: HSR per 15-min block next to a flat pass-completion line [Carling2011]. This shows the Verifier's honesty visually.
6. **"Not tired, tactical."** When running drops but the context check explains it ("3–0 up, sitting deep"), the agent says so. This is a responsible-AI moment judges can see.
7. **Reachable-area bubble.** Draw a circle each defender can reach in 1–2 s [Narizuka2023]. It shrinks slightly when tired, and shows clearly when the attacker is outside it.
8. **"Tug of war."** Both teams' running per minute on one live chart. Fans see one side raise the tempo and the other follow (r ≈ 0.7) [Allen2026a].
9. **"Work without the ball."** Live pressing meter: out-of-possession vs in-possession running per minute (TOOP/TIP), against the league range 0.99–1.23 [Allen2026b, Table 2].
10. **"Expected running."** Pre-match forecast of each team's distance from opponent, venue and expected possession, then live actual vs forecast [Castellano2024, Eq. 1, LaLiga coefficients, labelled "model"].
11. **"Turns."** Count of sharp changes of direction per player [Deutsch2025]; fan-friendly and easy to compute.

### 9.2 Fan-friendly names

| Technical | Fan name |
|---|---|
| D′ balance | **Battery** |
| Cumulative metabolic energy | **Tank** (or "Fuel used") |
| Equivalent distance | **"Felt like X km"** |
| Peak 1/2/5-min periods | **Red-zone spells** |
| Post-peak window | **Catching breath** |
| Recovered to normal | **Second wind** |
| Recovery runs and covering | **Getting back** |
| Pitch control | **Space owned** |
| Acceleration–speed profile | **Engine** (analyst only) |
| Out-of-possession running per minute | **Work without the ball** |
| TOOP/TIP ratio | **Pressing meter** |
| Change-of-direction count | **Turns** |

### 9.3 Analyst mode vs casual-fan mode

| | Casual fan | Analyst |
|---|---|---|
| Battery | 5-level icon; story cards at key moments | D′ balance trace with band; CS and D′ marked "assumed" |
| Numbers | Rounded; one per card; always "vs his normal" | Rolling 1/2/5-min HSR and sprint vs own power-law peak; metabolic power (rolling); VHIR recovery time; acceleration and deceleration bands |
| Explanations | One sentence from the claims register | Sources shown (citation keys), evidence grade, context-check result |
| Space | "Space owned" heat map at big moments | Pitch control at events, with the fresh counterfactual labelled "model" |
| Uncertainty | Implied by the icon levels | Explicit bands from validation; Buchheit note |

### 9.4 Features judges might like

- **Placebo-match validation** (6.2): a methods contribution no paper makes.
- **A Verifier that cites its sources.** Each sentence on screen carries a hover with the claim-register row and the citation key. This is explainability that judges can test.
- **"Evidence grade" badge** on each insight: ✅ / ⚠️.
- **Story controls tied to physiology.** Example: "Team A presses high for 60 min" sets a high load, and the fade emerges from the model rather than being scripted.
- **Estimator scorecard.** Estimated vs true battery for one match, with coverage of the uncertainty band, in the README and the video.
- **Multilingual narratives** generated from the claims-register templates, so translations keep the verified meaning.

---

## 10. Conversion problems (docling)

Check against the PDFs before reusing anything from these `.md` files.

**Unreliable, so do not use the .md for numbers:**

| Paper | Problem |
|---|---|
| Buchheit2015 | The .md is the title page only |
| DiSalvo2007 | The .md is the abstract only |
| SilvaJR2018 | 5.7 MB; all tables collapsed into giant lines |
| Hills2018 | 1.5 MB; Tables 1–3 collapsed or jumbled |
| Skiba2012 | Scanned PDF; OCR errors; Eqs. 3–5 missing; abstract r² shown as 0.11 |
| Wang2024 | Tables 2–3 collapsed into giant lines |
| Allen2026b | .md starts mid-introduction (abstract lost); Table 2 rows merged (Everton–Southampton); Table 5 cells blank. Abstract from the PDF |
| Morgans2025b | .md starts mid-introduction (first page lost) |
| Allen2025 | All values in figure images (Figs 1–3); .md has none |

**Equations missing or garbled; use the PDF:** Skiba2021 (all equations dropped), Chorley2023 (Eqs. 4–8 garbled to single characters; use pdftotext -layout), Lievens2024 (Eqs. 1–2), Weigend2023 (hydraulic equations are in Weigend 2021, not in our set), Osgnach2010, diPrampero2005, Mizelman2024 (Table 1), Jones2017, Narizuka2023, Spearman2017, Spearman2018, Fernandez2018 (appendix), daSilva2025, Bou2026.

**Key tables garbled or missing:**

| Paper | Problem |
|---|---|
| Ju2022 | Table 2 |
| Carling2011 | Table I |
| Bradley2013 | Tables II–IV |
| Thoseby2022 | Tables 1–2 |
| Thoseby2023 | Tables 1–2 |
| Kavanagh2024 | Table 3 |
| Fang2024 | Table 3 |
| Mohr2003 | Table 1 |
| Rampinini2008 | Table 1 |
| Russell2011 | Table 1 |
| Krustrup2006 | Table 2; "±" shown as "T" |
| Morin2021 | Table 1: minus signs lost |
| Mizelman2024 | Table 3: rows shifted |
| Bortnik2022 | Table 3 |
| Dambroz2022 | Table 5 missing |
| Bangsbo2006 | Table II |
| Schimpchen2020 | No tables at all |
| Chen2025 | Table 1 (match events) garbled; all physical values in Figs 1–2 |
| Castellano2025 | Tables 2 and 4 garbled; Table 3 fine in pdftotext -layout |
| Chorley2023 | Table 2 header lost; column order inferred |
| VighLarsen2018 | Table 1 placeholder in .md; scrambled in the PDF layout text (accepted manuscript) |
| Alonso-Callejo2024 | Table 1 cells missing; use the PDF |
| Morgans2025c | Tables 1–6 garbled |
| Allen2024 | Tables 4 and 6 scrambled (columns merged, rows shifted); Table 5 header garbled. `pdftotext -layout` on the PDF gives Tables 4–5 cleanly |

**Figures are the only source of key values** (not in any .md): Allen2025 (Figs 1–3: all running-load values and calibration equations are in images), Morgans2025, daSilva2025, Sutcliffe2025, Bortnik2022, Akenhead2013, Fang2024 (Fig. 1), Russell2011 (Fig. 4), Mohr2005.

**Good conversions:** Leifsson2024, Cortez2026, Niu2026, Liu2021, Paul2015, SilvaH2025, Bradley2009, Sutcliffe2025 (text), Bassek2025 (text).
