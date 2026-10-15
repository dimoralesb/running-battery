# Thoseby2023: Peak 1–10 min running demands by position and half
Citation: Thoseby B, Govus AD, Clarke AC, Middleton KJ, Dascombe BJ (2023). Positional and temporal differences in peak match running demands of elite football. Biology of Sport 40(1):311–319. DOI: 10.5114/biolsport.2023.116006
Type: match study
Context: Australian A-League (Hyundai A-League), one professional team, 3 seasons (same club and period as Thoseby2022), 68 matches, 44 outfield players, 508 match files (13 ± 10 per player, range 1–43). Included only if the player played > 70 min. Positions (players / files): AM 6 / 68, CD 10 / 118, DM 6 / 91, STR 4 / 46, WD 9 / 105, WNG 9 / 80. Team mostly played 4-2-1-3. GPS: STATSports "18 Hz (10 Hz GNSS)", between the shoulder blades; 4th-order Butterworth 1 Hz filter; speeds > 10 m/s and |accel| > 6 m/s^2 set to zero. (p. 312)
Evidence strength: medium. Proper mixed models with a random player intercept and effect sizes with a pre-set "worthwhile" cut-off (SMD > 0.6). But one team, small position groups (only 4 strikers, 46 files), A-League level, GPS. Effect sizes use the within-player residual SD, which is smaller than a between-player SD, so the SMDs look larger than a classic Cohen's d would.

## Definitions and thresholds
- TD: total distance per minute (m/min).
- HSD: distance > 19.8 km/h = 5.5 m/s, per minute (m/min).
- AveAcc: mean of absolute accelerations and decelerations in the window (m/s^2) (p. 312).
- Peak demand: maximum rolling average over windows 1–10 min, per half; then fitted with a power-law curve per position and half (p. 313).
- SMD bands: trivial < 0.2, small 0.2–0.6, moderate 0.6–1.2, large 1.2–2.0, very large 2.0–4.0. "Worthwhile difference" = SMD > 0.6 (p. 313).
- Positions: AM attacking midfielder, CD central defender, DM defensive midfielder, STR striker, WD wide defender (full-back), WNG/WIN winger.

## Key numbers   (each with page/table/figure)

### Whole-half outputs (Table 1, p. 313), mean ± SD; m/min in brackets
| Variable | Half | AM | CD | DM | STR | WD | WNG |
|---|---|---|---|---|---|---|---|
| Half duration (min) | 1st | 47 ± 1 | 47 ± 1 | 47 ± 1 | 47 ± 1 | 47 ± 1 | 47 ± 1 |
| | 2nd | 50 ± 1 | 50 ± 2 | 50 ± 2 | 49 ± 2 | 50 ± 2 | 50 ± 2 |
| TD (m) | 1st | 5645 ± 362 (119 ± 10) | 5070 ± 469 (107 ± 10) | 5261 ± 623 (111 ± 13) | 4742 ± 376 (101 ± 8) | 5036 ± 410 (106 ± 9) | 5396 ± 549 (114 ± 11) |
| | 2nd | 5624 ± 543 (114 ± 12) | 5078 ± 457 (102 ± 10) | 5308 ± 376 (106 ± 8) | 4627 ± 412 (94 ± 8) | 5087 ± 471 (103 ± 10) | 5362 ± 720 (107 ± 14) |
| | Match | 11269 ± 689 (116 ± 8) | 10149 ± 835 (104 ± 9) | 10569 ± 863 (109 ± 9) | 9369 ± 723 (97 ± 7) | 10123 ± 764 (105 ± 8) | 10758 ± 1142 (110 ± 11) |
| HSD > 5.5 m/s (m) | 1st | 354 ± 102 (7 ± 2) | 248 ± 101 (5 ± 2) | 255 ± 106 (5 ± 2) | 270 ± 68 (6 ± 1) | 337 ± 124 (7 ± 3) | 450 ± 135 (9 ± 3) |
| | 2nd | 347 ± 113 (7 ± 2) | 267 ± 118 (5 ± 2) | 253 ± 91 (5 ± 2) | 254 ± 87 (5 ± 2) | 349 ± 127 (7 ± 3) | 449 ± 148 (9 ± 3) |
| | Match | 701 ± 171 (7 ± 2) | 515 ± 195 (5 ± 2) | 508 ± 169 (5 ± 2) | 524 ± 110 (5 ± 1) | 687 ± 222 (7 ± 2) | 899 ± 259 (9 ± 3) |
| AveAcc (m/s^2) | 1st | 0.63 ± 0.06 | 0.61 ± 0.05 | 0.65 ± 0.05 | 0.57 ± 0.02 | 0.62 ± 0.05 | 0.64 ± 0.06 |
| | 2nd | 0.59 ± 0.07 | 0.57 ± 0.07 | 0.61 ± 0.04 | 0.53 ± 0.04 | 0.59 ± 0.06 | 0.60 ± 0.07 |
| | Match | 0.61 ± 0.06 | 0.59 ± 0.05 | 0.63 ± 0.04 | 0.55 ± 0.03 | 0.60 ± 0.05 | 0.62 ± 0.06 |
Key point (p. 316): absolute TD and HSD (in metres) are the same in both halves. The 2nd half is ~3 min longer (more stoppage), so TD per minute drops ~5–7 m/min for CD, DM, STR, WNG (marked "greater than second half" in Table 1). Table 1 flags 1st > 2nd relative TD for CD, DM, STR, WNG. Positional (SMD > 0.6): AM > CD, WD, STR for TD (ES 1.63–2.04, p. 313); WNG > all but AM for HSD (ES 1.56–2.7). No positional differences for whole-half AveAcc.

### Peak demand power-law fits (Table 2, p. 316), mean (90% CI)
Model: peak(t) = intercept × t^slope, t in minutes (see Equations).
| Metric | Half | AM | CD | DM | STR | WD | WNG |
|---|---|---|---|---|---|---|---|
| TD intercept (m/min) | 1st | 199 (188–211) | 180 (159–205) | 187 (163–214) | 182 (157–211) | 188 (165–215) | 189 (166–216) |
| | 2nd | 190 (176–205) | 178 (150–210) | 185 (155–221) | 177 (146–214) | 186 (156–221) | 188 (158–223) |
| TD slope | 1st | −0.17 | −0.17 | −0.16 | −0.18 | −0.18 | −0.18 |
| | 2nd | −0.16 | −0.18 | −0.17 | −0.20 | −0.19 | −0.19 |
| HSD intercept (m/min) | 1st | 53 (44–63) | 42 (28–63) | 42 (27–65) | 45 (28–72) | 51 (33–78) | 59 (39–90) |
| | 2nd | 48 (37–62) | 43 (24–76) | 41 (23–75) | 41 (21–79) | 50 (28–91) | 58 (32–104) |
| HSD slope | 1st | −0.63 | −0.68 | −0.66 | −0.63 | −0.60 | −0.59 |
| | 2nd | −0.60 | −0.64 | −0.63 | −0.68 | −0.59 | −0.61 |
| AveAcc intercept (m/s^2) | 1st | 1.05 (1.00–1.10) | 1.02 (0.92–1.13) | 1.06 (0.95–1.18) | 1.01 (0.89–1.14) | 1.07 (0.96–1.19) | 1.05 (0.94–1.17) |
| | 2nd | 1.01 (0.95–1.08) | 0.97 (0.83–1.13) | 1.02 (0.87–1.19) | 0.94 (0.79–1.12) | 1.01 (0.86–1.17) | 1.03 (0.88–1.20) |
| AveAcc slope | 1st | −0.18 | −0.17 | −0.17 | −0.19 | −0.18 | −0.17 |
| | 2nd | −0.18 | −0.17 | −0.19 | −0.19 | −0.18 | −0.19 |
(Slope CIs in Table 2: TD about ±0.01–0.05; HSD ±0.03–0.2; AveAcc ±0.01–0.06. 2nd-half CIs are about twice as wide as 1st-half CIs.)

### Peak values per window, computed from Table 2 (my calculation: intercept × t^slope)
I checked these against Fig. 1 and Fig. 2 (pp. 314–315); they match the plotted means within ~1–3 m/min (TD), ~1–2 m/min (HSD) and ~0.02 m/s^2 (AveAcc) (approx., read from Figs. 1–2).

Peak TD (m/min):
| Position | 1st: 1 / 3 / 5 / 10 min | 2nd: 1 / 3 / 5 / 10 min |
|---|---|---|
| AM | 199 / 165 / 151 / 134 | 190 / 159 / 147 / 131 |
| CD | 180 / 149 / 137 / 122 | 178 / 146 / 133 / 118 |
| DM | 187 / 157 / 145 / 129 | 185 / 154 / 141 / 125 |
| STR | 182 / 149 / 136 / 120 | 177 / 142 / 128 / 112 |
| WD | 188 / 154 / 141 / 124 | 186 / 151 / 137 / 120 |
| WNG | 189 / 155 / 142 / 125 | 188 / 153 / 139 / 121 |

Peak HSD > 5.5 m/s (m/min):
| Position | 1st: 1 / 3 / 5 / 10 min | 2nd: 1 / 3 / 5 / 10 min |
|---|---|---|
| AM | 53 / 26.5 / 19.2 / 12.4 | 48 / 24.8 / 18.3 / 12.1 |
| CD | 42 / 19.9 / 14.1 / 8.8 | 43 / 21.3 / 15.4 / 9.9 |
| DM | 42 / 20.3 / 14.5 / 9.2 | 41 / 20.5 / 14.9 / 9.6 |
| STR | 45 / 22.5 / 16.3 / 10.5 | 41 / 19.4 / 13.7 / 8.6 |
| WD | 51 / 26.4 / 19.4 / 12.8 | 50 / 26.1 / 19.3 / 12.9 |
| WNG | 59 / 30.9 / 22.8 / 15.2 | 58 / 29.7 / 21.7 / 14.2 |

Peak AveAcc (m/s^2):
| Position | 1st: 1 / 3 / 5 / 10 min | 2nd: 1 / 3 / 5 / 10 min |
|---|---|---|
| AM | 1.05 / 0.86 / 0.79 / 0.69 | 1.01 / 0.83 / 0.76 / 0.67 |
| CD | 1.02 / 0.85 / 0.78 / 0.69 | 0.97 / 0.80 / 0.74 / 0.66 |
| DM | 1.06 / 0.88 / 0.81 / 0.72 | 1.02 / 0.83 / 0.75 / 0.66 |
| STR | 1.01 / 0.82 / 0.74 / 0.65 | 0.94 / 0.76 / 0.69 / 0.61 |
| WD | 1.07 / 0.88 / 0.80 / 0.71 | 1.01 / 0.83 / 0.76 / 0.67 |
| WNG | 1.05 / 0.87 / 0.80 / 0.71 | 1.03 / 0.84 / 0.76 / 0.67 |

Authors' summary ranges (p. 317): peak TD 112–199 m/min, peak HSD 8–59 m/min, peak AveAcc 0.60–1.07 m/s^2 across positions and windows.

### Between-half differences in peaks (Fig. 2, p. 315; text p. 316), worthwhile = SMD > 0.6, 1st > 2nd
| Position | Peak TD | Peak HSD | Peak AveAcc |
|---|---|---|---|
| AM | 1–2 min windows (marker in Fig. 2 only; not mentioned in text) | none | none |
| CD | none | none | none |
| DM | none | none | 2–10 min windows (ES 0.61–0.81) |
| STR | 4–10 min windows (ES 0.60–0.89) | 7–10 min windows (ES 0.62–0.68) | all 1–10 min windows (ES 0.62–0.84, shared range with WD) |
| WD | none | none | all 1–10 min windows (ES 0.62–0.84) |
| WNG | none | none | 7–10 min windows (markers in Fig. 2; abstract lists WNG, text and discussion do not) |
Size: STR peak 10-min TD ~120 → ~112 m/min (−7%); STR peak 10-min HSD ~10.5 → ~8.6 m/min (−18%); STR peak 1-min AveAcc 1.01 → 0.94 m/s^2 (−7%); WD 1-min AveAcc 1.07 → 1.01 (−6%) (from Table 2 fits). Peak 1-min HSD 2nd-half drops are not worthwhile for any position (STR 45 → 41, CI wide).

### Positional differences in peaks (Fig. 1, p. 314; text p. 316)
- TD: AM > all others for most windows in the 1st half (ES 0.62–1.63); AM > all but DM in the 2nd half (ES 0.70–2.08). CD and STR lowest.
- HSD: AM, WD, WNG > CD and DM in 1st-half windows (ES 0.61–1.61); CD, DM and STR < AM, WD, WNG in the 2nd half (ES 0.60–1.61). Abstract: WNG > CD, DM, STR in both halves (ES 0.78–1.61).
- AveAcc: STR lower than all positions except CD, 1st half (ES 0.63–1.02) and 2nd half (ES 0.63–1.12).

## Equations     (LaTeX, with variable definitions and units; mark "checked against PDF")
Power-law peak-demand curve (the paper names it "power law" with intercept and slope, citing Delaney 2018 and Katz & Katz 1994, but does not print the formula; the form below is the standard one and reproduces Fig. 1 values from the Table 2 parameters, which I checked against the PDF figures):
$$P(t) = c \, t^{\,n}$$
- $P(t)$: peak rolling-average demand for window length $t$ (m/min for TD and HSD; m/s^2 for AveAcc)
- $t$: window length (min), 1 ≤ t ≤ 10
- $c$: intercept = predicted 1-min peak (same units as $P$)
- $n$: slope (dimensionless, negative): TD ≈ −0.16 to −0.20, HSD ≈ −0.59 to −0.68, AveAcc ≈ −0.17 to −0.19
Equivalent log form: $\ln P = \ln c + n \ln t$.
Parameters checked against PDF Table 2. Formula form not printed in the paper.

AveAcc definition as in Thoseby2022 (mean of $|a_i|$ over the window).

## Limitations
- One team (4-2-1-3), so position results are partly this team's tactics. The authors say so (p. 317).
- Strikers: 4 players, 46 files. The striker second-half drop could be about 4 people.
- > 70 min players only: substitutes and early-replaced players are excluded.
- Reporting is inconsistent on which positions drop AveAcc in the 2nd half: abstract says DM, WD and WNG (plus STR for all metrics); results text says STR, WD (all windows) and DM (2–10 min); discussion says DM, STR, WD; Fig. 2 shows STR, WD, DM and WNG (7–10 min only). The AM 1–2 min TD drop appears only in Fig. 2.
- 2nd half is ~3 min longer; peaks are rolling windows, so they are not affected by half length directly, but more stoppages mean fewer long uninterrupted spells.
- Effect sizes based on within-subject residual SD (p. 313): not comparable with between-player Cohen's d in other papers.
- GPS 10 Hz AveAcc depends on filtering; the authors note their AveAcc is higher than an earlier A-League study (0.60–1.07 vs 0.52–0.90 m/s^2) because of processing differences (p. 317). Do not mix with optical-tracking accelerations.
- No contextual factors (score, opponent, possession).
- The inclusion rule (> 70 min) is justified by citing Thoseby2022 as showing most peaks occur before the 70th minute (p. 312), but Thoseby2022 reports within-half timing, so that justification is loose.

## Use in Second Wind
- Simulator: use the Table 2 power-law parameters as per-position targets for peak 1–10 min TD, HSD (> 5.5 m/s) and AveAcc in synthetic matches, with a correction for league/system (A-League GPS, not EPL optical). In the 2nd half, keep peak TD and HSD the same for most positions, but lower peak AveAcc by ~4–7% for STR, WD and DM (and WNG over long windows), and lower STR long-window TD (−5 to −7%) and long-window HSD (~−15 to −20%). Keep whole-half metres equal across halves; per-minute values fall only because the 2nd half is ~3 min longer.
- Fatigue estimator: "rolling 1/2/5-min HSD vs player's own peak": the 1-min peak HSD is 2.5–4 times the 10-min peak (slope ≈ −0.6), so thresholds must be window-specific. A generic "50% of 1-min peak" rule would fire constantly over 5-min windows. Use P(t) = c t^n per player to set the reference for any window length.
- Agents / claims: allowed: "strikers and full-backs typically show smaller acceleration peaks after half-time" (A-League evidence, one team). Not allowed: "everyone's peak sprinting drops in the second half": peak HSD is kept for most positions, and absolute HSD metres are kept for all positions.
- Overlay / UI: a per-position "peak curve" small chart (window length vs peak m/min) with the player's current rolling value as a dot. Shows how close a player is to his peak for 1, 3, 5 min.

## Ideas or questions it raised
- READING_LIST.md claim ("Peak demands are lower in the second half for strikers (all metrics) and for acceleration in several positions") is broadly right but imprecise: (1) for strikers, TD peaks fall only for 4–10 min windows and HSD peaks only for 7–10 min windows, so short 1–3 min striker bursts are NOT reduced; (2) "several positions" = STR, WD (all windows), DM (2–10 min) and WNG (7–10 min, figure only); AM and CD keep their acceleration peaks; (3) n = 4 strikers, one team; (4) the paper itself is inconsistent about which positions (see Limitations).
- Accel peaks drop in the 2nd half while TD/HSD peaks do not. This fits Akenhead2013 (accel/decel declines) and suggests acceleration capacity is the more fatigue-sensitive signal. It supports the Morin acceleration-speed profile check in the estimator.
- We could fit P(t) = c t^n on each synthetic player per half and compare n with these slopes as a realism metric.
- Question: the CD 2nd-half HSD intercept is slightly higher than the 1st (43 vs 42). Is that chasing late in games? Only score data could tell.

Conversion quality: partial — body text fine in the docling .md; Table 1 and Table 2 are broken into scrambled multi-column rows (Table 2 nearly unreadable). Figures are images only. Values taken from pdftxt and checked against the PDF; per-window values computed from Table 2 and visually checked against Figs. 1–2.
