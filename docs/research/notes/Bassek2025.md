# Bassek2025: IDSSE open dataset (DFL position + event data, 7 matches)
Citation: Bassek M, Rein R, Weber H, Memmert D (2025). An integrated dataset of spatiotemporal and event data in elite soccer. Scientific Data 12:195. doi:10.1038/s41597-025-04505-y. Data: figshare doi:10.6084/m9.figshare.28196177. Code for the paper figures: github.com/spoho-datascience/idsse-data.
Type: dataset (data descriptor)
Context: German Bundesliga (2 matches) and 2. Bundesliga (5 matches), season 2022/23, elite men. 7 matches, 10 teams, 207 players. Official DFL data: TRACAB Gen5 optical tracking (16–20 cameras, 1920 × 1080, 25 Hz), plus DFL event data annotated live by trained operators (PDF pp. 2, 3).
Evidence strength: high as a data source (official league data, documented process, validated tracking system). Low for generalising: 7 matches, and **5 of 7 are Fortuna Düsseldorf home matches** (all five 2. Bundesliga matches), so team style is not balanced.

## Definitions and thresholds
| Item | Content | Source |
|---|---|---|
| Files per match | 3 XML files: match information, events, position data | p. 2 |
| Totals | 207 players, 10 teams, 11,137 events, 1,002,644 frames | p. 2 |
| Licence | CC BY 4.0, with DFL authorisation | pp. 1–2 |
| Download | figshare (ref 31); also via Python `floodlight` (`floodlight.io.dfl` for raw files, `floodlight.io.datasets` for direct access); paper used floodlight v0.4.0 | pp. 2, 9 |
| Definitions | DFL "Catalogue of Definitions Official Match Data" v5.1 (2020) | p. 2, ref 34 |
| Video | Not included (licensing) | p. 2 |
| Match information | Competition, season, matchday, kick-off time (ISO 8601), teams and IDs; stadium, capacity, **pitch size (m)**, weather (°C, % humidity, hPa), spectators; teams with jersey colours and **formation** (one of 41 templates, picked by an operator); players with ID, name, shirt number, **position code** (German abbreviations, Fig. 2), starter flag, captain; staff; referees; **gross and net playing time per half (s)** | pp. 2–4, Box 1 |
| Event data | Hierarchical classes: player actions (on-ball, tackles, fouls, offside, other), team actions (set pieces, counter-attacks), referee actions (whistles, substitutions, cards). Each event has an ISO 8601 timestamp, ID, and attributes such as x/y in m and xG | p. 4, Table 2, Box 2 |
| Main event attributes | Play (pass/cross): SemiField, Player, Team, FromOpenPlay, PenaltyBox, FlatCross, Height, Distance, PlayOrigin, PlayAngle, Recipient, BallPossessionPhase, Evaluation. TacklingGame: Winner/Loser (+team, role), PossessionChange, GoalKeeperInvolved, Type. ShotAtGoal: xG, PlayerSpeed, Pressure, DistanceToGoal, AngleToGoal, InsideBox, CounterAttack, etc. Foul: Fouler, Fouled, FoulType | Table 2, p. 5 |
| "Delete" events | Events deleted in post-processing; no content (≈1,070 of them, approx. from Fig. 3) | Table 2, Fig. 3 |
| Position data (per player, per half) | Frame number N, timestamp T (ISO 8601), X, Y (m), D = distance since previous frame (**cm**), S = speed (**km/h**), A = acceleration (m/s²), M = minute of play | p. 5, Box 3 |
| Ball extra fields | Z (height), BallPossession (1 = home, 2 = away), BallStatus (0 = dead, 1 = in play) | p. 5 |
| Position metadata | Match ID, pitch size (Box 3: 105.00 × 68.00 m), start time | p. 5, Box 3 |
| Frame rate | 25 Hz (camera rate p. 2; Box 3 timestamps step 0.04 s; ≈ 137–147k frames per match fits ≈ 92–98 min at 25 Hz) | p. 2, Box 3, Table 1 |
| Coordinates | Position data: origin at **pitch centre** (ball at kick-off X = 0.18, Y = −0.17, Box 3). Event data: origin at a **corner** (kick-off X = 52.50, Y = 34.00, Box 2). Our reading of Boxes 2–3; the paper does not state it | Boxes 2–3 |

## Key numbers   (each with page/table/figure)
Matches (Table 1, p. 3):
| Match ID | Div | Home | Away | Result | xG | Date | Frames | Events |
|---|---|---|---|---|---|---|---|---|
| J03WMX | 1 | 1. FC Köln | FC Bayern München | 1:2 | 1.33:1.18 | 2023-05-27 | 145,967 | 1,840 |
| J03WN1 | 1 | VfL Bochum | Bayer Leverkusen | 3:0 | 1.97:0.78 | 2023-05-27 | 141,561 | 1,459 |
| J03WPY | 2 | Fortuna Düsseldorf | 1. FC Nürnberg | 0:1 | 1.01:1.78 | 2022-10-15 | 146,211 | 1,579 |
| J03WOH | 2 | Fortuna Düsseldorf | SSV Jahn Regensburg | 4:0 | 2.66:0.52 | 2022-08-26 | 137,214 | 1,457 |
| J03WQQ | 2 | Fortuna Düsseldorf | FC St. Pauli | 1:0 | 1.25:1.09 | 2022-11-05 | 142,345 | 1,679 |
| J03WOY | 2 | Fortuna Düsseldorf | Hansa Rostock | 3:1 | 2.14:0.43 | 2022-09-10 | 142,536 | 1,578 |
| J03WR9 | 2 | Fortuna Düsseldorf | 1. FC Kaiserslautern | 1:2 | 1.16:1.31 | 2022-11-11 | 146,810 | 1,545 |
Events per match (all types): mean ≈ 1,591, range 1,457–1,840 (our calculation from Table 1). Both Bundesliga matches are from the last matchday (34).

Shots and goals (p. 6):
| Item | Value |
|---|---|
| Shots with xG | 171 (≈ 24.4 per match) |
| Goals | 19 (≈ 2.7 per match) |
| Sum of xG | 18.42 |
| xG per shot | mean 0.11 ± 0.15, median 0.05, range 0.01–0.85 |
| DFL xG model | 10 features (shot location, shooter speed, defenders in line, GK position, pressure, body part, ball control before shot and at gaining possession, after free kick, is free kick); trained on 105,627 Bundesliga shots; most important: distance to goal, GK distance to goal, angle |

Event counts, all 7 matches (approx., read from Fig. 3 log axis, p. 6; per match = /7):
| Event | Total (approx.) | Per match (approx.) |
|---|---|---|
| Play_Pass | ≈ 5,200 | ≈ 740 |
| OtherBallAction | ≈ 1,700 | ≈ 240 |
| TacklingGame | ≈ 1,400 | ≈ 200 |
| Delete | ≈ 1,070 | ≈ 150 |
| ThrowIn_Play_Pass | ≈ 275 | ≈ 39 |
| BallClaiming | ≈ 200 | ≈ 29 |
| Foul | ≈ 155 | ≈ 22 |
| FreeKick_Play_Pass | ≈ 150 | ≈ 21 |
| Play_Cross | ≈ 140 | ≈ 20 |
| OutSubstitution | ≈ 125 | ≈ 18 (seems high for 5 subs per team; check in data) |
| GoalKick_Play_Pass | ≈ 117 | ≈ 17 |
| ShotAtGoal_ShotWide | ≈ 63 | ≈ 9 |
| CornerKick_Play_Cross | ≈ 53 | ≈ 7.6 |
| ShotAtGoal_SavedShot | ≈ 41 | ≈ 5.9 |
| ShotAtGoal_BlockedShot | ≈ 37 | ≈ 5.3 |
| Caution | ≈ 37 | ≈ 5.3 |
| ShotAtGoal_SuccessfulShot | ≈ 16 (+ 3 penalty goals = 19 goals, matches p. 6) | ≈ 2.3 |
| Offside | ≈ 16 | ≈ 2.3 |
Passes + shots synchronised: n = 6,251 (≈ 893 per match) (p. 8).

Data quality (pp. 6–8):
| Check | Result | Source |
|---|---|---|
| TRACAB vs VICON (30 × 30 m area; soccer-specific course plus small-sided game, 10 athletes; Linke et al. 2020) | RMSE position 0.06–0.18 m; velocity 0.03–0.09 m/s; acceleration 0.06–0.27 m/s². Errors grow at higher speeds | p. 7 |
| Missing frames | None found in the validation study; operators check data live and after the match | p. 8 |
| ID swaps | Possible when players are close; fixed by operators | p. 8 |
| Event–tracking time offset (raw vs synced) | −0.37 ± 1.82 s, max 27.34 s | p. 8, Fig. 7 |
| Event x/y vs ball position, raw | 9.37 ± 8.39 m, max 58.61 m | p. 8 |
| After sync (DataBallPy v0.5.3, cost functions + Needleman–Wunsch idea) | 2.61 ± 3.60 m, max 75.35 m | p. 8 |
| Sync applied in the released files? | No. Automatic sync methods "have not been applied to this dataset". The paper's sync was only an evaluation | p. 5 |
| Advice | Low-pass filter before deriving velocity/acceleration, especially in high-intensity moments | pp. 7–8 |

## Equations     (LaTeX, with variable definitions and units; mark "checked against PDF")
None in the paper. Unit conversions needed when loading (from the field definitions, p. 5):
$$v\,[\text{m/s}] = S\,[\text{km/h}] / 3.6, \qquad d\,[\text{m}] = D\,[\text{cm}] / 100$$
Checked against PDF (p. 5, Box 3).

## Limitations
- Only 7 matches; 5 are Fortuna Düsseldorf home matches; no Premier League; German 2nd division dominates. Running numbers may differ from the Premier League.
- Event timestamps are not synchronised with tracking in the released data. Raw offsets average −0.37 s with SD 1.82 s (max 27 s). We must sync ourselves (DataBallPy, or kloppy/floodlight tools) before per-event analysis.
- Events and positions appear to use different coordinate origins (corner vs centre; our reading of Boxes 2–3). Check when loading.
- Our observation from Box 3: in the first ball frames, D = 57.78 cm per 0.04 s (≈ 14.4 m/s) while S still reads ≈ 2 km/h for 4 frames. The provided S seems smoothed or lagged. Recompute speed from X/Y with our own filter for calibration.
- TRACAB error rises with speed (p. 7), which matters for sprint and peak-speed statistics.
- The paper does not mention kloppy. Loader support there (DFL/Sportec format) is outside this paper and must be checked separately.
- No physical summary numbers (distances, speeds per position) are reported. We have to compute them ourselves.
- No heart rate, GPS or physiological data. No fatigue ground truth.

## Use in Running Battery
- Simulator: the best real 25 Hz source for (after downsampling to 10 Hz) speed and acceleration distributions per position code, distances per half, high-speed running, and v95 per half (to compare with daSilva2025 Fig. 1). Also event mix and rates (≈ 740 open-play passes, ≈ 200 duels, ≈ 24 shots, ≈ 22 fouls, ≈ 39 throw-ins, ≈ 7.6 corners per match, approx.). Gross/net playing time per half sets the effective ball-in-play time. BallStatus gives dead-ball periods. Formation and position codes give target-position templates. Coordinate system: 105 × 68 m. XML layout and field names (N, T, X, Y, D, S, A, M; BallPossession, BallStatus) are a ready-made schema to imitate.
- Fatigue estimator: test the estimator's input pipeline on real positions (smoothing, speed, acceleration, metabolic power). Check that a CS/D′ fit from tracking runs on real data. Per-player minute-by-minute high-speed running for peak-spell detection. No ground truth, so this is a "does it look plausible" check only.
- Agents / claims: none directly. If we quote "calibrated on official Bundesliga data", add "7 matches, 5 of them 2. Bundesliga".
- Overlay / UI: real frames for UI development only offline. Keep the repo free of the raw data (PLAN §2.2). CC BY 4.0 allows fitted parameters plus attribution.

## Ideas or questions it raised
- READING_LIST says "Our main open dataset (CC BY 4.0). Data format and how to download it." Correct. PLAN.md says the dataset gives "fatigue patterns over 90 min". With 7 matches, 5 of them home matches of one team, that is a weak basis. Use it for distributions and pipeline tests, not for fatigue curves (those come from Leifsson2024 / Schimpchen2020 / Mohr2003).
- The PLAN table cites the PMC link and "7 Bundesliga / 2. Bundesliga matches (2022/23)". Correct; full citation: Sci Data 12:195.
- Ask the organisers (PLAN §2.2) whether calibration on CC BY data is fine. The licence itself allows it with attribution.
- Useful check: compute v95 per half for IDSSE players and compare with daSilva2025 Fig. 1 (LaLiga, ≈ 5.1–5.4 m/s medians). If similar, the 5 m/s pitch-control default holds for our synthetic players.

Conversion quality: good for text and Table 1 (correct in the .md). Partial overall: Boxes 1–3 (XML examples, which hold the coordinate and unit evidence) and Fig. 3 (event counts) are images, so they are missing from the .md and were read from the PDF.
