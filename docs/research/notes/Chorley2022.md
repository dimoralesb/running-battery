# Chorley2022: Bi-exponential W′ reconstitution in trained cyclists
Citation: Chorley A, Bott RP, Marwood S, Lamb KL. Bi-exponential modelling of W′ reconstitution kinetics in trained cyclists. Eur J Appl Physiol 2022;122:677–689. doi:10.1007/s00421-021-04874-3 (open access)
Type: lab study
Context: 10 trained amateur cyclists (9 M, 1 F; 41 ± 10 y; VO2max 58.6 ± 7.1 ml·kg⁻¹·min⁻¹), cycle ergometer. Repeated ramps to exhaustion, recovery 15–360 s at 50 W, 5–9 sessions each.
Evidence strength: medium. Small, cycling, recovery after **full** exhaustion only.

## Definitions and thresholds
- W′ fully depleted by ramp + step-down to CP + 30 W; W′ reconstitution = work above CP in the next ramp.
- Bi-exponential: %W′rec = FCamp·(1 − e^(−t/τFC)) + SCamp·(1 − e^(−t/τSC)), amplitudes sum to 100%.

## Key numbers   (each with page/table/figure)
- Group fit, first recovery (Abstract): **FC amplitude 50.7%, τFC 21.5 s; SC amplitude 49.3%, τSC 388 s.** AICc bi 30.2 vs mono 72.2 (abstract) / 17.0 vs 72.2 (shared-amplitude model, Results).
- Second recovery: W′ reconstitution −9.1 ± 7.3% at 180 s and −8.2 ± 9.8% at 240 s; modelled **τSC rises to 716 s**, τFC unchanged (Abstract).
- Individual fits: FCamp 47.7 ± 17.8%; τFC 22.0 ± 11.8 s (R1), 16.3 ± 6.6 s (R2); τSC 377 ± 100 s (R1), 549 ± 226 s (R2); mono τ 125 ± 53 s (R1) (Results, "Model selection"; Table 2).
- Fast component >90% complete by 50 s; slow component reaches 90% at 892 s (R1) and 1650 s (R2) (Fig. 4).
- Bigger absolute W′ → bigger share in the slow component (r = 0.66).
- Individual AICc did not differ between bi and mono (p = 0.46) overall; bi won in 6/10 participants.

## Equations
Bi-exponential form above (Eq. 7 in paper); prediction equations from 30 s and 240 s recoveries exist (Eq. 10–13) but are superseded by Chorley2023. Docling kept the text; equations checked only through the text.

## Limitations
- Full exhaustion only; Lievens2024 found mono fits better after partial depletion.
- Cycling; recovery at 50 W only (low intensity).
- Small n, large individual variation.

## Use in Running Battery
- Simulator: values for a **two-pool truth model**: fast pool ~50%, τ ~20 s; slow pool ~50%, τ ~400 s, slowing to ~550–700 s after repeated hard efforts. Our current truth (τ₁ 60 s, τ₂ 330 s, 60/40 split; synthesis §3.2.4) has a fast pool that is too slow.
- Fatigue estimator: no change (one pool).
- Agents / claims: "fatigue builds over repeated efforts because the slow part of recovery gets slower" is supported in cycling lab data only.
- Overlay / UI: none.

## Ideas or questions it raised
- The slowing of τSC after repeated efforts is a mechanism for late-match decline that a one-pool model misses.
