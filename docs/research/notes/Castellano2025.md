# Castellano2025: Physical profiles by position in the five top European leagues (SkillCorner)
Citation: Castellano J, Huarte X, Casamichana D. Match physical performance profiles in professional football: a comparative analysis among players' positions in the European five top leagues. Int J Perform Anal Sport 2025;25(1):108–128 (online Aug 2024). doi:10.1080/24748668.2024.2393034
Type: match study (multi-league, player level)
Context: 2022/23 season, Bundesliga, Ligue 1, LaLiga, **Premier League**, Serie A. 3,211 player-position profiles (CD 592, FB 627, CM 822, WN 515, FW 655); players with ≥ 70 min in a match; values averaged per player and **normalised to 98 min**. **SkillCorner broadcast tracking** (single camera).
Evidence strength: medium-high for counts and shapes (large, recent, multi-league); absolute values carry broadcast-tracking error.

## Definitions and thresholds
- RUN 15–20 km/h (4.17–5.56 m/s); HSR 20–25 km/h (5.56–6.94 m/s); SPR > 25 km/h (6.94 m/s).
- Counts (nHSR, nSPR, mACC 1.5–3 m/s², hACC > 3 m/s², mDEC −1.5 to −3, hDEC < −3) need **≥ 0.7 s** duration.
- VMAX = 99th percentile of speed.

## Key numbers   (each with page/table/figure)
**Per position, mean ± SD per 98 min, all five leagues pooled (Table 3, read from PDF layout text):**

| | CD | FB | CM | WN | FW |
|---|---|---|---|---|---|
| TD (m) | 10,210 ± 511 | 10,913 ± 561 | 11,665 ± 673 | 11,207 ± 752 | 11,030 ± 803 |
| HSR 20–25 km/h (m) | 415 ± 81 | 645 ± 119 | 637 ± 139 | 715 ± 129 | 659 ± 127 |
| Sprint > 25 km/h (m) | 138 ± 45 | 248 ± 76 | 167 ± 74 | 257 ± 94 | 236 ± 84 |
| **HSR efforts (n)** | 34.7 ± 6.0 | 53.7 ± 8.0 | 51.4 ± 10.6 | 61.1 ± 9.8 | 56.8 ± 9.8 |
| **Sprint efforts (n)** | **7.2 ± 2.3** | **12.7 ± 3.3** | **8.8 ± 3.7** | **14.0 ± 4.7** | **13.2 ± 4.4** |
| Acc 1.5–3 (n) | 89.0 ± 9.2 | 103.0 ± 9.7 | 99.9 ± 11.0 | 99.2 ± 11.1 | 100.4 ± 12.8 |
| Acc > 3 (n) | 5.8 ± 1.6 | 8.4 ± 2.7 | 5.8 ± 2.4 | 9.3 ± 3.6 | 9.0 ± 3.1 |
| Dec −1.5/−3 (n) | 72.6 ± 7.1 | 84.7 ± 8.0 | 90.8 ± 9.1 | 88.2 ± 10.2 | 84.0 ± 9.5 |
| Dec < −3 (n) | 13.3 ± 2.5 | 20.7 ± 3.6 | 16.1 ± 4.1 | 21.9 ± 5.0 | 20.3 ± 4.3 |
| VMAX (km/h) | 28.7 ± 1.1 | 29.4 ± 1.2 | 27.8 ± 1.3 | 29.2 ± 1.5 | 29.1 ± 1.4 |

- **Premier League vs LaLiga (mixed model, Table 4):** TD −197 m; HSR distance +9.6 m (ns); HSR efforts +2.2; sprint distance +11.2 m; sprint efforts +0.2 (ns); mACC +5.7; hACC +0.5; mDEC +2.7; hDEC ns; VMAX +0.3 km/h. PL had the least TD and the most accelerations/decelerations of the five leagues (Results).
- **SkillCorner vs TRACAB (Methods 2.3):** TD bias 403.7 m (LoA −366 to +1,173 m); **VMAX bias −2.1 km/h (−0.58 m/s), LoA −4.5 to +0.3 km/h**. Broadcast tracking under-reads top speed.
- PCA: two components (75.6% variance): volume (TD, RUN, HSR, mACC, mDEC) and intensity (sprint, VMAX, hACC, hDEC) (Table 1).

## Equations
None.

## Limitations
- Broadcast tracking (players off-camera are estimated), 0.7 s effort rule; VMAX biased low.
- Pooled leagues in Table 3; PL-specific position values not given.
- Docling garbled Table 2 and Table 4; Table 3 OK only in the PDF layout text.

## Use in Second Wind
- Simulator: **fills the gap on effort counts.** Sprint efforts per match ~7 (CD) to ~14 (WN); HSR efforts ~35–61; high decelerations outnumber high accelerations ~2.5:1. Use as targets for count shapes; scale distances with Allen2024/2025 instead.
- Fatigue estimator: also relevant because **SkillCorner open data is one of our calibration sources**: expect its VMAX to read ~0.6 m/s low and TD ~0.4 km different vs TRACAB.
- Agents / claims: "Premier League players accelerate and decelerate more often than in other top leagues" → supported (small effects).
- Overlay / UI: fan metric "bursts" (high accelerations + sprints) has realistic ranges here.

## Ideas or questions it raised
- When we calibrate on SkillCorner open data, apply a top-speed correction or use percentiles below the max.
