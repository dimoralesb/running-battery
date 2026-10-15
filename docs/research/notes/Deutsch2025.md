# Deutsch2025: Change of direction frequency and intensity in the Bundesliga
Citation: Deutsch JP, Donath L, Braunstein B, Rein R. Frequency and intensity of change of directions in German Bundesliga soccer. Sci Med Football 2025;9(4):399–411 (online Dec 2024). doi:10.1080/24733938.2024.2439859
Type: match study (league-wide) + detection algorithm
Context: Bundesliga 2016/17, 18 teams, 308 matches, 401 players, 5,066 full-match observations (≥ 90 min). TRACAB Gen4, 25 Hz, natural grass.
Evidence strength: high for counts within this method (whole league); method-dependent.

## Definitions and thresholds
- **Pre-processing (Methods, "Data analysis"):** positions smoothed with a **zero-lag 4th-order Butterworth low-pass, 1 Hz cut-off**; velocity and acceleration by central differences (floodlight package); remove |a| > 10 m/s² and v > 10.5 m/s.
- **COD event:** deceleration ≤ −2.0 m/s², then a direction change ≥ 20°, then acceleration ≥ 2.0 m/s²; no 1-s time limit. Angle = 180° − angle between the deceleration vector (start→end of decel) and the acceleration vector (start→end of accel).
- Entry speed bands < 3.0, 3.0–5.5, 5.5–7.0, > 7.0 m/s; angle bands 20–59°, 60–119°, 120–180°.

## Key numbers   (each with page/table/figure)
- **Total CODs per match (Table 1):** GK 51.4 ± 15.7; CB 95.2 ± 23.1; FB 103.7 ± 23.5; **CM 107.4 ± 23.5**; WM 100.6 ± 24.6; ST 81.4 ± 21.7. CV ~22–27% for outfield players.
- Distribution (Abstract): ~55% of CODs below 3.0 m/s entry, ~38% at 3.0–5.5, ~7% above 5.5 m/s; angles ~5% (20–59°), ~25% (60–119°), **~70% (120–180°)**.
- Typical COD (Table 5): total length 1.4 ± 0.5 s; mean deceleration −3.0 ± 0.8 m/s²; mean acceleration 2.8 ± 0.7 m/s²; entry 2.9 ± 1.5 m/s; exit 2.6 ± 1.3 m/s; decel distance 1.2 ± 1.2 m.
- FB and WM do most high-speed (> 5.5 m/s) CODs; CM most low-speed CODs.

## Equations
Angle: θ = 180° − arccos( (V₁·V₂) / (|V₁||V₂|) ) (Methods; from text, not checked against image).

## Limitations
- One season, 2016/17; no context (phase, score).
- Heavy 1 Hz filter smooths short movements; counts depend on it.

## Use in Second Wind
- Simulator: realistic **turn counts and shapes** (~80–110 per outfield player per match, mostly sharp turns at low speed). Our movement model should include sharp low-speed turns, not only straight runs.
- Fatigue estimator: **gives us a published, reproducible preprocessing recipe for 25 Hz optical data** (Butterworth 1 Hz zero-lag + central differences + sanity cut-offs), filling the gap in synthesis §3.1. Same package (floodlight) we plan to use for IDSSE.
- Agents / claims: none on fatigue (no time course).
- Overlay / UI: "turns" counter, fan-friendly ("he changed direction 30 times in 15 minutes").

## Ideas or questions it raised
- A drop in high-speed CODs late in a match could be another observable fatigue signal; no paper tests it.
