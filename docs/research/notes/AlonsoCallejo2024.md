# AlonsoCallejo2024: Validity and reliability of the in-situ acceleration–speed profile
Citation: Alonso-Callejo A, García-Unanue J, Guitart-Trench M, Majano C, Gallardo L, Felipe JL. Validity and reliability of the acceleration-speed profile for assessing running kinematics' variables derived from the force-velocity profile in professional soccer players. J Strength Cond Res 2024;38(3):563–570. doi:10.1519/JSC.0000000000004637 (open access)
Type: validation study
Context: 14 players of a Spanish elite club's second team (20.8 ± 1.9 y), one competitive week (Nov 2022). **WIMU PRO GPS 10 Hz.** Reference: 30-m sprint force–velocity profile (linear encoder 500 Hz, My Sprint app, GPS).
Evidence strength: medium-low. Small n, reserve team, GPS, one week.

## Definitions and thresholds
- ASP fitted following Morin2021: speeds ≥ 3 m/s, 0.2 m/s bins, two highest accelerations per bin, linear fit, outliers outside 95% CI removed; ~60 points per profile.
- ASP1 = 5 training sessions + match (~6,000 observations); ASP2 = training only (~4,000); **ASP3 = match only (~800)**.

## Key numbers   (each with page/table/figure)
- Profiles (Table 1, from PDF): A0 7.21 ± 0.48 (ASP1), 6.68 ± 0.50 (ASP2), **6.34 ± 0.57 m/s² (ASP3)**; S0 9.77 ± 0.55, 9.42 ± 0.86, 9.21 ± 0.63 m/s; reference encoder F0 7.56 ± 0.60 N/kg, V0 9.48 ± 0.36 m/s.
- **Agreement with encoder (Table 2):** ASP1 A0 ICC 0.505, S0 ICC 0.708; **ASP3 (match only) A0 ICC 0.227, MAE 1.30; S0 ICC 0.38, MAE 0.52; Vmax ICC 0.30**.
- Relative systematic error ASP1 vs devices: A0 −2.8 to −4.5% (± ~8%); S0 0.7–3.0% (± ~4–5%) (Discussion).
- Recommendation: **at least 5–6 sessions** for a reliable ASP; for a match-only profile, at least 5–6 matches (Discussion; Practical applications).

## Equations
None (ASP method as Morin2021).

## Limitations
- Reserve-team players, GPS, one week; A0 vs F0 compare different units.
- A0 is extrapolated below 3 m/s, so its error is larger.

## Use in Second Wind
- Simulator: player capacity (A0 ~6.5–7.5 m/s², S0 ~9.2–9.8 m/s) as truth parameters; consistent with Morin2021.
- Fatigue estimator: **a single match does not give a reliable A–S profile** (A0 ICC 0.23). A within-match "capacity check" is weaker still. Take the A–S profile from **metadata (season/week profile)**, and in-match use only "share of runs near the player's own limit".
- Agents / claims: "his top-end acceleration has dropped in this match" → **not supported** from tracking alone.
- Overlay / UI: capacity check stays analyst-only, or drop it.

## Ideas or questions it raised
- Confirms the decision in synthesis §3.6 and strengthens it: move the capacity check from "low confidence" to "not shown live".
