# Schimpchen2020: Sequences of peak intensity and the minutes after them (one Portuguese 2nd-tier team, GPS)
Citation: Schimpchen J, Gopaladesikan S, Meyer T. The intermittent nature of player physical output in professional football matches: an analysis of sequences of peak intensity and associated fatigue responses. European Journal of Sport Science. Accepted manuscript online 28 May 2020; issue 2021, 21(6):793–802 (volume/pages taken from Leifsson2024's reference list; the PDF we have is the accepted manuscript without them). doi:10.1080/17461391.2020.1776400
Type: match study
Context: one team in the **second tier of Portuguese senior football**, all 34 matches of 2018/19 (the paper does not name the team; authors are from Sport Lisboa e Benfica's Human Performance Department, so most likely Benfica's B team). 29 players, age 20.4 ± 2.8 y, full-match appearances only: 237 match files, 236 used (8.2 ± 7.9 per player). Positions: 6 CD (61 files), 6 FB (61), 11 CM (59), 2 W (42), 4 ST (13); formation 4-3-3. GPS Catapult OptimEye S5, raw velocity exported at **10 Hz**; satellites 11.9 ± 0.2, HDOP 0.7 ± 0.1 (manuscript pp.4–5, PDF pp.5–6).
Evidence strength: medium. Good method (10 Hz raw velocity, rolling windows, mixed model with player as random effect, ES and 95% CI) but one young second-tier team, small n, uneven player contribution, only minutes 1, 3 and 5 after the peak, no positional analysis, no control for regression to the mean.

## Definitions and thresholds
| Item | Definition | Source |
|---|---|---|
| TD | total distance (m/min) | ms p.5 (PDF p.6) |
| HID | high-intensity distance at ≥ 5.0 m/s (18.0 km/h) — **lower than Leifsson's 5.5 m/s** | ms p.5 |
| Acc/Dec | average of the absolute acceleration/deceleration values over the window (a mean |a|, given in "m·min⁻²" in the tables; physically m/s² averaged) | ms p.5 |
| Data cleaning | drop samples > 10 m/s or Doppler acc/dec > 6 m/s²; need ≥ 6 satellites, HDOP ≤ 2; drop files with > 2% discarded data | ms p.5 |
| SPI (sequence of peak intensity) | highest rolling window of 1, 5 or 10 min, every sample used as a start point; 9 SPIs per player-match (3 metrics × 3 windows) | ms p.6 (PDF p.7) |
| Post-SPI analysis | output in the **1st, 3rd and 5th minute** after the SPI vs that player's match-average per-minute output (the average **includes** the peak). Analysed in the same metric (Table 1) and as TD (Table 2). SPIs ending < 5 min before half-time or full-time dropped (238 of 2124 analyses) | ms p.6 |
| Context | SPI end time put in six 15-min periods; goal difference at SPI end in 5 classes | ms p.6 |
| Stats | linear mixed model (player random effect); Cohen's d (< 0.2 trivial, 0.2–0.5 small, 0.5–0.8 medium, > 0.8 large); χ² goodness-of-fit and binomial tests with adjusted α (0.004, 0.005) | ms p.7 (PDF p.8) |

## Key numbers   (each with page/table/figure)
Context for all: Portuguese 2nd tier, 2018/19, GPS 10 Hz, HID ≥ 5.0 m/s. Values are mean ± SD or mean difference [95% CI].

**Table 1 (ms p.16, PDF p.17) – same metric after its own SPI, vs match average**
| Metric / window | SPI rate | Match avg/min | Min 1 diff [95% CI] (ES) | Min 3 diff (ES) | Min 5 diff (ES) |
|---|---|---|---|---|---|
| HID 1-min | 77.66 ± 21 m/min | 10.8 ± 3.9 | −6.96 [−8.65; −5.27] (0.94) | −0.44 [−2.7; 1.82] (0.13) | −3.31 [−4.78; −1.85] (0.29) |
| HID 5-min | 28.2 ± 8.4 | 10.8 ± 3.9 | −7.98 [−9.1; −6.86] (0.95) | −2.78 [−4.34; −1.22] (0.24) | −2.17 [−4.12; −0.21] (0.47) |
| HID 10-min | 20.9 ± 6.4 | 10.8 ± 3.9 | −9.6 [−10.87; −8.32] (0.95) | −4.6 [−6.3; −2.89] (0.74) | −0.66 [−3.07; 1.75] (0.12) |
| TD 1-min | 200.5 ± 20.2 | 107.3 ± 11.2 | −11.33 [−15.87; −6.78] (0.75) | +0.36 [−4.39; 5.11] (0.01) | +0.51 [−3.93; 4.96] (0.02) |
| TD 5-min | 143.6 ± 14.2 | 107.3 ± 11.2 | −17.71 [−23.68; −11.74] (0.83) | +5.38 [1.18; 9.57] (0.17) | +5.17 [0.02; 10.31] (0.43) |
| TD 10-min | 132.0 ± 13.0 | 107.3 ± 11.2 | −13.4 [−17.08; −9.72] (0.44) | +1.19 [−4.17; 6.55] (0.11) | +1.72 [−3.07; 6.51] (0.05) |
| Acc/Dec 1-min | 0.82 ± 0.08 | 0.44 ± 0.03 | −0.05 [−0.07; −0.03] (0.76) | −0.01 [−0.03; 0.01] (0.06) | +0.01 [−0.01; 0.03] (0.34) |
| Acc/Dec 5-min | 0.58 ± 0.05 | 0.44 ± 0.03 | −0.08 [−0.09; −0.06] (0.91) | +0.01 [−0.01; 0.02] (0.05) | +0.01 [−0.01; 0.04] (0.27) |
| Acc/Dec 10-min | 0.53 ± 0.04 | 0.44 ± 0.03 | −0.07 [−0.09; −0.06] (0.87) | −0.01 [−0.03; 0.01] (0.29) | +0.01 [−0.01; 0.03] (0.28) |

**Same as % of match average (text, ms pp.7–8, PDF pp.8–9)**
| Metric / window | Min 1 | Min 3 | Min 5 |
|---|---|---|---|
| HID 1-min | −64.4% | −4.1% (trivial, CI includes 0) | −30.6% (small) |
| HID 5-min | −73.9% | −25.7% (small) | −20.1% (small) |
| HID 10-min | −88.9% | −42.6% (moderate) | −6.1% (trivial, CI includes 0) |
| TD 1-min | −10.6% | +0.3% | n.r. (+0.5%) |
| TD 5-min | −16.5% | +5% | n.r. (+4.8%) |
| TD 10-min | −12.5% | +1.1% | n.r. |
| Acc/Dec 1-min | −11.4% | −2.3% | n.r. |
| Acc/Dec 5-min | −18.2% | +2.3% | n.r. |
| Acc/Dec 10-min | −15.9% | −2.3% (small) | n.r. |

**Table 2 (ms p.17, PDF p.18) – TD after each SPI, vs match TD 107.3 ± 11.2 m/min**
| SPI type | Min 1 TD diff [95% CI] (ES) | Min 3 | Min 5 |
|---|---|---|---|
| after HID 1-min SPI | −8.96 [−13.08; −4.84] (0.28) = −8.4% | +2.25 [−1.82; 6.33] | −6.13 [−10.78; −1.48] (0.17) |
| after HID 5-min SPI | −8.47 [−12.54; −4.39] (0.28) = −7.9% | −3.89 [−9.01; 1.24] (0.37) = −3.6% | −3.15 [−7.93; 1.64] |
| after HID 10-min SPI | −11.98 [−16.63; −7.33] (0.72) = −11.2% | −4.81 [−9.5; −0.12] (0.41) = −4.5% | −0.45 [−6.21; 5.31] |
| after Acc/Dec 1-min SPI | −7.47 [−13.13; −1.82] (0.51) = −7% | −1.1 | +0.74 |
| after Acc/Dec 5-min SPI | −6.4 [−10.25; −2.55] (0.21) = −6% | +6.62 [2.5; 10.74] | +5.69 [0.96; 10.42] (0.67) |
| after Acc/Dec 10-min SPI | −7.71 [−12.36; −3.07] (0.62) = −7.2% | +0.92 | +5.13 [0.46; 9.8] |

**Table 3 (ms p.19, PDF p.20) – number of SPIs per 15-min period (n = 236 per row; expected 39.3)**
| Metric / window | 0–15 | 15–30 | 30–45 | 45–60 | 60–75 | 75–90 | χ² p |
|---|---|---|---|---|---|---|---|
| HID 1 | 42 | 42 | 39 | 41 | 36 | 36 | .38 |
| HID 5 | 37 | 40 | 50 | 35 | 38 | 36 | .22 |
| HID 10 | 33 | 41 | 53 | 29 | 38 | 42 | .38 |
| TD 1 | 60* | 37 | 41 | 33 | 29 | 36 | .01 |
| TD 5 | 96* | 37 | 35 | 48 | 11† | 9† | < .001 |
| TD 10 | 102* | 38 | 40 | 34 | 17† | 5† | < .001 |
| Acc 1 | 70* | 37 | 45 | 27 | 27 | 30 | < .001 |
| Acc 5 | 112* | 41 | 25 | 40 | 11† | 7† | < .001 |
| Acc 10 | 108* | 40 | 45 | 29 | 10† | 4† | < .001 |
(* more, † fewer than an equal split, p < 0.004.) The **size** of SPIs did not differ between first and last 15 min for any metric (ms p.8–9). Fig. 1 (PDF p.22, approx.): peak 1-min HID ~75–80 m/min and 5/10-min ~25–30 m/min in every 15-min period.

**Table 4 (ms p.20, PDF p.21) – SPIs by goal difference.** Minutes played: draw 1469, +1 goal 660, −1 goal 507, +≥2 goals 238, −≥2 goals 186 (of 3060). HID SPIs matched the expected split in every window. Fewer SPIs than expected only for TD 5-min when winning by ≥ 2 (4 vs 18), TD 10-min when losing by ≥ 2 (1 vs 14) and Acc/Dec 10-min when losing by ≥ 2 (3 vs 14) (ms p.9).

**Recovery time constant (my derivation, not in paper).** HID 10-min window: −89% → −43% → −6% at min 1, 3, 5 gives τ ≈ 1.5 min overall (2.7 min for min 1→3, 1.0 min for min 3→5). HID 5-min window: −74% → −26% → −20%, τ ≈ 1.9 min for min 1→3, then a plateau around −20%. HID 1-min window is not monotonic (−64%, −4%, −31%), so no single τ fits; this suggests noise or a second effect. TD and Acc/Dec: back to match average by minute 3, so τ < 1 min.

## Equations     (LaTeX, with variable definitions and units; mark "checked against PDF")
Acc/Dec load (described in words, ms p.5; formula written by me, checked against the text only):
$$ \overline{|a|}_{W} = \frac{1}{N_W}\sum_{i \in W} |a_i| $$
a_i = acceleration of sample i (m/s², from Doppler velocity at 10 Hz), W = window, N_W = samples in the window.
Percent changes in the text = mean difference / match average × 100 (checked: e.g. −6.96/10.8 = −64.4%).

## Limitations
- One team, second tier, young players (20.4 y); most data from a "core" of players (authors, ms p.12). Not elite top-tier.
- HID threshold 5.0 m/s ≠ Leifsson 5.5 m/s and ≠ Mohr2003 video categories; GPS vs optical; absolute values not comparable.
- Only minutes 1, 3, 5 analysed; no minute 2 or 4.
- Match average includes the peak itself, which inflates the reference (so % drops look larger than with Leifsson's reference).
- No positional analysis (authors, ms p.12). No control for regression to the mean; authors mention high match-to-match variability of high-speed running as a possible explanation (ms p.10).
- Acc/Dec is a mean of |a|, mixing accelerations and decelerations; no "high Acc/Dec" category.
- The PDF is the accepted manuscript (watermarked), not the final typeset version; page numbers here are manuscript pages.

## Use in Second Wind
- Simulator: second calibration curve for temporary fatigue in high-speed running: about −64 to −89% in minute 1, about −4 to −43% at minute 3, about −6 to −31% at minute 5 (≥ 5 m/s). Total distance and mean |a| must drop only ~10–18% in minute 1 and be back by minute 3. Peaks of high-speed running should be spread evenly over the match and not depend on score; peaks of total distance and mean |a| should mostly occur in the first 15 min and rarely in the last 30 min.
- Fatigue estimator: supports tracking high-speed running separately from total distance. A TD-based fatigue signal will miss most of the temporary effect. Expect a large post-peak drop in HSR for 3–5 min.
- Agents / claims: supported: "after his most intense spell of high-speed running, players typically run much less at high speed for the next few minutes, while their total running is back to normal within about 3 minutes." Avoid: "fatigue was independent of the score" — only the timing/count of peak HID spells was independent of score; the post-peak response was not tested by score.
- Overlay / UI: a two-line mini chart (HSR vs TD) after a peak could show that only high-speed output stays low.

## Ideas or questions it raised
- READING_LIST check: "Benfica, full season" – imprecise: it is a team in the **second tier** of Portuguese football (paper does not name it; authors from Benfica, so probably Benfica B), young squad, 2018/19, 29 players, GPS 10 Hz. "Total distance recovers within 3 min" – correct. "HID 64–89% lower in the first minute" – correct, but HID is ≥ 5.0 m/s, not 5.5. "Still 6–31% lower at minute 5" – numbers correct, but the −6% (10-min window) is not significant (CI crosses 0), and for the 1-min window the drop is only −4% (n.s.) at minute 3, then −31% at minute 5 (non-monotonic). "HID peaks don't depend on score or match time" – correct for the **number** of peak HID spells per period/score and for their size across halves; it says nothing about post-peak recovery by score.
- The non-monotonic 1-min curve suggests minute-level noise and/or tactical rhythm (e.g., phases of play). Our simulator should produce similar noise; do not over-fit a smooth exponential.
- TD and Acc/Dec peaks cluster in the first 15 min (pacing or match tempo), HID peaks do not: players may protect high-speed capacity for when it is needed (authors' pacing interpretation, ms p.12).

Conversion quality: partial — the .md has the full text but **none of the four tables** (watermarked accepted manuscript); tables read from pdftotext and checked visually on PDF pp.17–18; Fig. 1 is a tiny box plot (PDF p.22).
