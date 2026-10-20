# Cortez2026: Physical, tactical and technical performance in and after the 1-min most demanding passage (World Cup 2022)
Citation: Cortez A, Yousefian F, Folgado H, Brito J, Travassos B, Abade E, Liu H, Niu Z, Gonçalves B (2026). Physical, tactical and technical performance of the most demanding passages of kinematic activity in elite soccer. BMC Sports Science, Medicine and Rehabilitation 18:195. doi:10.1186/s13102-026-01645-5 (received 2025-08-11, accepted 2026-02-27)
Type: match study
Context: FIFA World Cup Qatar 2022, international elite. All 64 matches. 1,016 observations from 399 outfield players who started and played ≥ 70 min (FB 89 players, CD 80, WM 93, CM 93, CF 44; observation counts per position not given). Data from the official FIFA Data Platform; optical multi-camera tracking TRACAB (ChyronHego), HD cameras at 25 Hz (p. 2).
Evidence strength: medium. Elite, complete tournament, optical 25 Hz, mixed models. But: one tournament, only 1-min windows, the reference is the peak itself (strong selection effect), technical variables are only counts, ball-in-play drops sharply in the Post minute, and the paper has internal inconsistencies (abstract vs results) and odd values in Table 3.

## Definitions and thresholds
- MDPk (kinematic most demanding passage): the **1-min rolling** window with the most distance at ≥ 15 km/h (≥ 4.17 m/s) (p. 2). Decomposed into MSR 15–19.8 km/h (4.17–5.5 m/s), HSR 19.8–25.2 km/h (5.5–7.0 m/s), SPR > 25.2 km/h (> 7.0 m/s), plus TD (p. 3). Note HSR here is a band that excludes sprinting (unlike Fang2024/Ju2022, where HIR > 19.8 km/h includes sprints).
- Post: the 1 min immediately after the MDPk. MDPs ending < 1 min before half-/full-time were removed (p. 3).
- Variables computed "during effective playing time" (Tables 2 and 3 titles); how effective time was applied to 1-min windows is not explained.
- Tactical/technical variables (Table 1, p. 3):
  - Team tactical: AttPerc (% of ball-in-play time in possession), BiPPerc (% ball in play), PsnTeam (% possession), PsnChg (possession changes, only possessions > 5 s).
  - Team technical: OppShot, OppPass, TeamShot, TeamPass (counts).
  - Individual tactical: SpExIndex (spatial exploration index, m), DefDrct / OffDrct (% of x-movements toward own / opponent goal), % time in own / central / opponent third.
  - Individual technical: Attempt (shots, n), Pass (passes, n).
- **There is no success-rate / accuracy variable at all.** Every technical variable is a count.
- Stats: GLMM (SAS), non-clinical MBI. ES = (mean Post − mean MDP) / SD MDP; < 0.2 trivial, 0.2–0.6 small, 0.6–1.2 moderate, 1.2–2.0 large, > 2.0 very large; 99% CI (p. 4). Covariates in the GLMM are not described (unlike Fang2024).

## Key numbers   (each with page/table/figure)

**Physical, MDP → Post (Table 2, p. 4; m/min)**

| Pos | TD | MDPk (≥ 15 km/h) | MSR | HSR (19.8–25.2) | SPR (> 25.2) |
|---|---|---|---|---|---|
| ALL | 190 ± 34 → 98 ± 24 (−48%, ES −3.6) | 111 ± 36 → 12 ± 14 (−89%, −6.9) | 51 → 8 (−84%, −4.0) | 39 ± 19 → 3 ± 8 (−93%, −5.5) | 20 ± 20 → 0.6 ± 26 (−97%, −3.8) |
| CD | 166 → 88 (−47%, −3.5) | 88 → 8 (−91%, −7.23) | 38 → 5 (−86%) | 30 → 2 (−94%, −5.3) | 18 → 0.6 (−97%, −4.1) |
| FB | 195 → 96 (−51%, −4.4) | 116 → 10 (−91%, −8.6) | 50 → 7.4 (−85%) | 40 → 2.4 (−94%, −6.3) | 24 → 0.3 (−99%, −6.2) |
| CM | 195 → 106 (−46%, −3.6) | 114 → 15 (−87%, −6.4) | 56 → 10 (−82%) | 40 → 3.7 (−91%, −5.05) | 16 → 0.9 (−94%, −2.8) |
| WM | 197 → 98 (−50%, −4.2) | 119 → 12 (−90%, −7.4) | 54 → 8.2 (−85%) | 39 → 2.8 (−93%, −5.5) | 25 → 1.0 (−96%, −4.2) |
| CF | 187 → 97 (−48%, −3.5) | 108 → 12 (−89%, −6.7) | 50 → 8.5 (−83%) | 39 → 3.0 (−92%, −5.5) | 18 → 0.7 (−97%, −3.4) |

**The −93% HSR compares the Post minute with the peak minute itself** (the single most intense 1-min window of the match), not with the match average. HSR in Post (3 m/min) vs a typical match average for elite players is not reported, so −93% says nothing about being below normal.

**Tactical and technical, MDP → Post (Table 3, p. 5; model means; % change computed by us)**

| Variable | ALL | CD | FB | CM | WM | CF |
|---|---|---|---|---|---|---|
| BiPPerc (%) | 82 → 57 | 73 → 53 | 85 → 59 | 81 → 59 | 84 → 58 | 83 → 56 |
| PsnChg (n) | 2.7 → 1.9 | 2.6 → 1.9 | 2.8 → 2.0 | 2.7 → 1.9 | 2.8 → 2.02 | 2.6 → 1.9 |
| AttPerc (%) | 50 → 46 | 49 → 45 | 50 → 47 | 48 → 48 | 51 → 47 | 50 → 43 |
| PsnTeam (%) | 48 → 43 | 47 → 43 | 48 → 43 | 46 → 44 | 50 → 44 | 49 → 44 |
| TeamPass (n) | 5.3 → 3.9 (−26%) | 4.6 → 4.2 | 5.5 → 3.9 | 5.6 → 4.3 | 5.7 → 4.1 | 5.2 → 3.04 |
| OppPass (n) | 5.6 → 4.04 (−28%) | 5.3 → 4.6 | 5.9 → 4.2 | 5.9 → 4.3 | 6.2 → 4.2 | 5.01 → 2.9 |
| TeamShot (n) | 0.18 → 0.087 | 0.16 → 0.034 | 0.095 → 0.083 | 0.011 → 0.006 | 0.22 → 0.12 | 0.11 → 0.075 |
| **Pass (n), player** | 0.66 → 0.36 (−45%) | 0.72 → 0.52 (−28%) | 0.66 → 0.35 (−47%) | 0.907 → 0.48 (−47%) | 0.601 → 0.26 (−57%) | 0.403 → 0.12 (−70%) |
| **Attempt (n), player** | 0.0037 → 0.00085 | 0.024 → 0.020 | 0.078 → 0.068 | 0.079 → 0.069 | 0.11 → 0.081 | 0.025 → 0.0065 (−74%) |
| SpExIndex (m) | 1835 → 1188 (−35%) | 1697 → 1094 | 1865 → 1229 | 1912 → 1200 | 1864 → 1179 | 1747 → 1238 |
| DefDrct (%) | 48 → 44 | 47 → 36.5 | 48 → 40 | 48 → 43 | 47 → 49 | 46 → 52 |
| OffDrct (%) | 45 → 43 | 43 → 47 | 47 → 47 | 47 → 46 | 47 → 39 | 48 → 35 |
| PlrOwn3rd (%) | 22 → 30 | 34 → 48 | 28 → 43 | 25 → 32 | 16 → 19 | 6.2 → 3.9 |
| PlrOpp3rd (%) | 22 → 20 | 15 → 6.8 | 20 → 10 | 19 → 18 | 28 → 34 | 42 → 51 |

**Standardized changes (approx., read from Fig. 1, p. 6; figure is a low-resolution raster in the PDF)**, all players: BiPPerc ~−0.85, PsnChg ~−0.7, SpExIndex ~−1.3, OppPass ~−0.3, TeamShot ~−0.2, DefDrct ~−0.25, Pass ~−0.4, Attempt ~−0.2, PlrOwn3rd ~+0.25; AttPerc, PsnTeam, OffDrct, PlrCntrl3rd trivial. Results text: "substantial decrements in BiPPerc, PsnChg and SpExIndex; small to trivial changes in all other tactical variables" (p. 5).

**Fewer actions vs worse actions:** every technical result in this paper is **fewer actions (volume)**. No pass accuracy, shot quality or duel outcome was measured. Moreover, ball-in-play falls from 82% to 57% of the Post minute (≈ −30% relative), so a large part of "fewer passes" is simply less ball-in-play time. Our rough check (assuming counts are per raw 1-min window): team passes per ball-in-play minute 5.3/0.82 ≈ 6.5 → 3.9/0.57 ≈ 6.8 (no drop); player passes per ball-in-play minute 0.66/0.82 ≈ 0.80 → 0.36/0.57 ≈ 0.63 (≈ −21%). If the counts are already per effective minute (as the table title suggests), this adjustment does not apply; the paper does not make this clear.

## Equations     (LaTeX, with variable definitions and units; mark "checked against PDF")
Effect size (p. 4, checked against PDF):
$$ES = \frac{\bar{x}_{Post} - \bar{x}_{MDP}}{SD_{MDP}}$$
$\bar{x}$ = GLMM-estimated mean of the variable in the 1-min MDP or the following 1 min; $SD_{MDP}$ = SD in the MDP minute. SpExIndex formula not given (cited ref. 41).

## Limitations
- Reference = the peak minute (selection effect / regression to the mean). A 1-min max window followed by any normal minute will show −80–95% in HSR.
- Ball-in-play drops 82 → 57% in Post: stoppages right after peaks (fouls, ball out, injuries, goals) explain much of the drop in running and in action counts. Authors themselves list "stoppages of a match" among possible causes (p. 6).
- Technical variables are counts only; no quality measure.
- Internal inconsistencies: the abstract says "all technical variables exhibited a substantial decline … regardless of playing positions", but the results say several technical variables were trivial for some positions (p. 5). The ALL value for Attempt (0.0037) is lower than every single position's value, which is impossible for a pooled mean; FB/CM/WM shot values exceed CF. Some SDs are implausible (SPR Post 0.6 ± 26; TeamShot CD 0.034 ± 5.3).
- GLMM covariates (score, opponent, venue) not described; context not clearly controlled.
- Single tournament, heat/short-recovery context, CF n = 44 players.
- No accelerations/decelerations (p. 7).

## Use in Running Battery
- Simulator: after a 1-min peak, the next minute has about half the total distance (≈ 98 m/min) and almost no HSR/sprint (3 and 0.6 m/min). Insert a likely stoppage/low-tempo minute after peaks: ball in play ~57% of the following minute vs ~82% in the peak minute. Defenders (CD, FB) drift to their own third after a peak (own-third time 34 → 48% CD, 28 → 43% FB); CF and WM stay higher (opp-third 42 → 51% CF).
- Fatigue estimator: do not treat "near-zero HSR in the minute after a peak" as evidence of fatigue by itself; it is the norm (and partly stoppage). The estimator should normalise by ball-in-play time.
- Agents / claims: Supported: "after the most intense minute, play usually calms down: less ball in play, fewer possession changes, fewer passes." Not supported: "his passing got worse after his sprint" (no quality data). If quoting −93%, must say "versus his most intense minute".
- Overlay / UI: could show a team "tempo" indicator (ball-in-play %, possession changes) next to the battery, to show context.

## Ideas or questions it raised
- READING_LIST.md check: "2022 World Cup (FIFA data)" correct; TRACAB 25 Hz. "In the minute after a peak passage, HSR drops 93%" correct but imprecise: it is vs the peak minute itself, and HSR here is 19.8–25.2 km/h only. "All technical variables drop" is the abstract's claim, but the results contradict it for some positions; and all of them are **counts** (fewer passes/shots), not worse actions. The READING_LIST warning ("check whether technical decline means fewer or worse") resolves to: **fewer**, partly explained by less ball in play. "Ball-in-play time and possession changes drop" correct (BiPPerc 82 → 57%, PsnChg 2.7 → 1.9). "Defenders spend more time in their own third" correct (CD, FB, CM).
- Ball-in-play falling after peaks is direct evidence for the "is it fatigue or context?" question: peaks are often followed by stoppages. Our simulator should create this pattern, and the agents should check it.
- Defenders' MDPs involve running toward their own goal (DefDrct higher in MDP), consistent with Ju2022's finding that recovery runs dominate peak spells.

Conversion quality: good — docling text and Tables 2–3 readable (a few cells missing, e.g. FB SpExIndex Post); Fig. 1 is a low-resolution raster in the PDF itself, so its values are only approximate.
