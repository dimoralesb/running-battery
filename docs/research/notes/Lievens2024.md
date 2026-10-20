# Lievens2024: W′ recovery after partial depletion
Citation: Lievens M, Ghijs M, Bourgois JG, Vermeire KM, Bourgois G, Colosio AL, Boone J, Caen K. Characterizing the exponential profile of W′ recovery following partial depletion. Med Sci Sports Exerc 2024;56(9):1770–1781. doi:10.1249/MSS.0000000000003468. **Our copy is the accepted manuscript ("Published ahead of Print"), unedited.**
Type: lab study
Context: 9 healthy, recreationally active men (physical-education students), cycle ergometer, Ghent. W′ depleted by 25% or 75% (1 or 3 min at P4), then 30, 60, 120, 300 or 600 s active recovery at 90% of gas-exchange threshold, then a second bout to exhaustion.
Evidence strength: medium. Small sample, cycling, recreational, but the only study of **partial** depletion, which is the football case.

## Definitions and thresholds
- W′OBS = time to exhaustion in bout 2 / 4 min (the expected TTE at P4).
- Mono-exponential vs bi-exponential fits, amplitude free or fixed; compared by RMSE and AICc (ΔAICc < 0 favours mono).
- Models tested: Skiba-1 τ = 546·e^(−0.01·D_CP) + 316; Skiba-2 τ = W′/D_CP; Bartram τ = 2287.2 × D_CP^(−0.688) (Methods, "Data analysis").

## Key numbers   (each with page/table/figure)
- **Model choice:** amplitude free → ΔAICc −15.5 (25% depletion) and −23.3 (75%): **mono-exponential preferred**. Amplitude fixed → −15.0 (25%), +11.2 (75%). Bi-exponential had lower RMSE (0.4–5.0% vs 2.9–8.0%) but over-fits (Abstract; Results; Table 2).
- **Mono τ: 32 s (25% depletion), 82 s (75%)**, with amplitudes 35% and 62% (Discussion).
- **First 30 s of recovery: +21.0 ± 16.7% (25%) and +23.0 ± 12.0% (75%) of W′**, not different. Speed of early recovery does not depend on how deep the depletion was (Results).
- After 75% depletion, recovery plateaued at **~83% of W′** within 10 min: incomplete recovery (Discussion).
- After small depletion, W′OBS exceeded 100% by up to ~11% at 10 min (priming effect).
- Existing models: average τ was 544 s (Skiba-1), 234 s (Skiba-2), 107 s (Bartram). For 25% depletion, Skiba-1 under-predicted recovery by 20.4 ± 5.0%, Skiba-2 by 15.5 ± 5.0%, Bartram by 11.1 ± 5.0% (trend) (Results, "Model comparisons"; Fig. 1C).
- Individual recovery is consistent: r = 0.92 between conditions; recovery relates to VO2peak, CP and GET (r = 0.67–0.77) (Fig. 2, Fig. 4).
- Perceived recovery was ~25.7 ± 4.5% lower than real recovery (Table 3).

## Equations
Equations 1–2 (mono, bi-exponential) are missing from the .md; the τ formulas above are in the text. AICc formula given (Equation 4).

## Limitations
- Cycling, recreational men, n = 9; group-mean fits on 5 time points.
- "Partial depletion" is assumed from the CP model, not measured.
- Recovery intensity fixed at 90% GET.

## Use in Running Battery
- Simulator: one-pool recovery is acceptable for partial depletion. Add a cap: after large depletion, recovery tops out below 100% for minutes (~83% here) → a natural source of **residual fatigue** for the end-of-match decline.
- Fatigue estimator: **supports a one-pool estimator.** Its fast τ (32–82 s) is cycling; in runners the fitted τ was ~5× slower than the standard formula [Bellenger2025], so we use τ = k·D′/(CS − v) with k ≈ 4 (synthesis §3.2.2).
- Agents / claims: "players recover a large share of their high-intensity capacity in the first 30 seconds" is supported in the lab (+21–23% of W′), with a cycling caveat.
- Overlay / UI: perceived vs real recovery gap is a nice story ("you feel worse than you are"), but it's cycling lab data; analyst mode only.

## Ideas or questions it raised
- Individual recovery speed is stable and tied to aerobic fitness: a per-player "recharge rate" parameter is justified.
