# Morin2021: In-situ acceleration-speed (A-S) profile from training GPS
Citation: Morin JB, Le Mat Y, Osgnach C, Barnabò A, Pilati A, Samozino P, di Prampero PE (2021). Individual acceleration-speed profile in-situ: a proof of concept in professional football players. Journal of Biomechanics 123:110524. doi:10.1016/j.jbiomech.2021.110524
Type: method (short communication, proof of concept)
Context: Italian first league (Serie A; club = Genoa CFC per affiliations), first team, 16 male professionals recruited (age 25.3 ± 3.8 yr, 78.9 ± 4.3 kg, 1.80 ± 0.1 m); 13 kept (≥ 5 training sessions of ~90 min in both phases). Period 20 Aug – 23 Sep 2018; two 2-week phases (Phase1 20 Aug–2 Sep; Phase2 10–23 Sep). TRAINING data only; official games excluded because players did not wear the GPS in games. GPS: GPEXE Pro2 (Exelio, Italy), 18 Hz (p. 2).
Evidence strength: medium. Professional players and simple, reproducible method, but small n (13), training only, one club, and two authors are consultants for the GPS company (conflict of interest, p. 4). No comparison with a sprint-test force-velocity profile.

## Definitions and thresholds
Method step by step (Section 2.2, p. 2):
1. Collect raw GPS speed over several sessions (≥ 5 sessions ≈ 500,000 raw points needed to cover 0 to max speed). Filter raw speed with a "custom Gaussian type procedure" (details not given), derive acceleration. Keep only positive accelerations.
2. Speed range for the fit: from 3 m/s (10.8 km/h) to the player's maximal speed reached. 3 m/s chosen because maximal accelerations are rarely seen below it (the centre of mass passes 3 m/s within the first step of a sprint start).
3. Bin speed in 0.2 m/s steps (3.0, 3.2, 3.4 …). In each bin keep the 2 highest acceleration values. This gives ~70 points.
4. Fit a first linear regression (acceleration on speed).
5. Remove outliers outside the 95% confidence interval (upper and lower) around the line.
6. Refit the linear regression on the remaining points: 52 ± 5 points (range 43–63).
7. Outputs: A0 = y-intercept (theoretical max acceleration, m/s²); S0 = x-intercept (theoretical max speed, m/s); AS_slope = −A0/S0 (1/s).
- Online tool: https://libm-lab.univ-st-etienne.fr/as-profile/#/home (csv with time, acceleration, speed) (p. 2).
- Reliability: change in mean and SEM between phases (Hopkins 2000) (p. 2).

## Key numbers   (each with page/table/figure)
Table 1 (p. 3), mean ± SD (min; max), n = 13:

| Variable | Phase1 | Phase2 | Change P2−P1 | Change % | SEM | SEM % |
|---|---|---|---|---|---|---|
| S0 (m/s) | 9.21 ± 0.43 (8.41; 9.92) [33.2 km/h] | 9.47 ± 0.52 (8.68; 10.3) [34.1 km/h] | 0.26 ± 0.43 | 2.86 | 0.30 | 3.31 |
| A0 (m/s²) | 7.70 ± 0.53 (6.55; 8.43) | 7.20 ± 0.40 (6.72; 7.84) | −0.50 ± 0.59 | −6.43 | 0.41 | 5.38 |
| AS_slope (1/s) | −0.839 ± 0.086 | −0.764 ± 0.070 | 0.08 ± 0.09 | −9.03 | 0.06 | 7.64 |

(The slope range is printed as (−0.976; −0.660) for both phases, which looks like a copy error in the paper.)

- Linearity: all R² > 0.984 (p. 2). Example player (Fig. 1, p. 3): 8 sessions over 2 weeks, > 700,000 raw points, 51 points selected, fit a = −0.857·v + 7.88, R² = 0.992, A0 = 7.88 m/s², S0 = 9.19 m/s.
- Reliability: random error (SEM) < 8% for all variables (p. 3). Systematic change between phases not negligible (A0 −6.4%, S0 +2.9%); cause unclear (method, devices, or real training changes) (p. 3).
- Comparison with sprint-test literature: S0 9–10 m/s vs V0 9.2–9.3 m/s; A0 7.2–7.7 m/s² vs F0 7.11–8.5 N/kg in professional players (p. 4).
- Minimum data: ≥ 5 training sessions (~90 min each) per 2-week phase used here (p. 2). The authors' "unpublished observations" say a profile may be obtained from one half or one full game, and from video tracking, if speed/acceleration are reliable (p. 4). This is not shown with data.
- Positions: not reported.

## Equations     (LaTeX, with variable definitions and units; mark "checked against PDF")
Checked against PDF (p. 2 text and Fig. 1/Table 1, p. 3, viewed as image). The paper defines A0, S0 and AS_slope = −A0/S0 in words; the explicit line equation below is the implied linear model (Fig. 1 shows y = −0.857x + 7.88).

$$a_{max}(v) = A_0 - \frac{A_0}{S_0}\,v = A_0\left(1 - \frac{v}{S_0}\right), \qquad AS_{slope} = -\frac{A_0}{S_0}$$

$a_{max}(v)$ = maximal forward acceleration a player can produce at running speed $v$ (m/s²); $v$ = running speed (m/s), fit range 3 m/s to player max; $A_0$ = theoretical maximal acceleration at $v = 0$ (m/s²); $S_0$ = theoretical maximal speed where acceleration is zero (m/s); $AS_{slope}$ in 1/s.

## Limitations
- Training only; game data not pooled (different systems) (p. 4). We work with match tracking, where efforts may be fewer but more maximal.
- Fit quality depends on GPS signal quality (environment, hardware, software) (p. 4). The Gaussian filter is not described in enough detail to reproduce.
- Not validated against force-velocity sprint tests here (p. 4). Minimal data amount not established (p. 4).
- Measures forward (tangential) acceleration in the running direction; curved runs and changes of direction are mixed into the cloud.
- Conflict of interest: Osgnach and di Prampero consult for Exelio (p. 4).

## Use in Second Wind
- Simulator: give each synthetic player A0 ~ N(7.5, 0.5) m/s² (range ~6.5–8.4) and S0 ~ N(9.3, 0.5) m/s (range ~8.4–10.3) from Table 1; use $a_{max}(v) = A_0(1 - v/S_0)$ as the propulsion limit in the motion model (fits the Narizuka-type first-order sprint model, where $\tau = S_0/A_0 \approx 1.2$ s). Fatigue can lower A0 and/or S0 in the hidden truth.
- Fatigue estimator: build a baseline A-S profile per player from the first part of a match (or earlier matches), then fit rolling profiles (e.g., per 15 min or per half) and compare A0, S0 against baseline. Use exactly the binning: 3 m/s minimum, 0.2 m/s bins, top-2 per bin, 95% CI outlier removal, refit. Be aware the data within 15 min may be too sparse to reach top speed (S0 extrapolation unstable).
- Agents / claims: supported: "A-S profile can be estimated from tracking without a test" (training GPS, pro players); "between-phase random error < 8%". Not supported by this paper: "A-S profile drops within a match due to fatigue" (not tested here).
- Overlay / UI: scatter of speed vs acceleration with the player's line (fresh vs now) is a clear, explainable visual.

## Ideas or questions it raised
- READING_LIST says "R² > 0.98" — correct (all R² > 0.984). It says "from normal tracking data": precise wording is "from GPS training data (18 Hz) over ≥ 5 sessions"; games were not used.
- Because changes between phases (−6% A0) are close to the SEM (5%), a within-match change must be larger than ~5–8% to be distinguishable from noise. Good default for an uncertainty band.
- With 10 Hz synthetic tracking we can test the minimum data needed per window (our own experiment).

Conversion quality: partial — text good, but Table 1 lost minus signs (slope shown as positive, A0 change shown as +0.50) and merged columns. Use the PDF.
