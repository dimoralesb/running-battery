# Chorley2023: A dynamic bi-exponential model of W′ that depends on recovery intensity
Citation: Chorley A, Marwood S, Lamb KL. A dynamic model of the bi-exponential reconstitution and expenditure of W′ in trained cyclists. Eur J Sport Sci 2023;23(12):2368–2378. doi:10.1080/17461391.2023.2238679
Type: lab study + model building
Context: 10 trained cyclists (9 M, 1 F; 43.6 ± 11.9 y; VO2max 60.0 ± 6.3), cycle ergometer. Full W′ depletion, recovery 30 s or 240 s at 50 W (LOW), 60% CP (MOD) or 85% CP (HVY). CP 293 ± 37 W, W′ 11.0 ± 2.9 kJ.
Evidence strength: medium-low for us. Small n, cycling, full depletion, model not validated on new data.

## Definitions and thresholds
- %D_CP = fractional difference between recovery power and CP (in %).
- Two pools; depletion shared between pools in proportion to what each still holds (Eq. 8a–8b).

## Key numbers   (each with page/table/figure)
- W′ reconstitution (Table 1), first recovery: 30 s → 36.8 ± 9.7% (LOW), 26.6 ± 6.8% (MOD), 21.7 ± 7.1% (HVY); 240 s → 63.1 ± 15.2%, 56.8 ± 15.1%, 41.0 ± 14.0%. Second recovery at HVY 240 s: 28.7 ± 7.3% (ES 1.3 vs first).
- Fitted parameters, means (Table 2; header garbled in .md, order inferred from text): **FCamp 36.0 ± 11.0%; τFC 15.0 ± 11.3 s (LOW), 28.0 ± 8.2 s (MOD), 35.0 ± 14.6 s (HVY); τSC 510 ± 295 s (LOW), 847 ± 653 s (MOD), 3221 ± 1818 s (HVY).**
- Prediction equations (PDF p.2373, checked against PDF text): FCamp = 0.75 × %W′(240 s at 85% CP) + 5.26 (6a); **τFC = 45·e^(−0.014·%D_CP) + 9999·e^(−0.811·%D_CP)** (6b); **τSC = 9999·e^(−0.098·%D_CP) + 429** (6c); second-recovery drop %W′rec2 = 0.72 × %W′rec1 + 0.18 × %D_CP (7).
- Check (derived, CP 293 W): LOW (%D_CP ≈ 83) → τFC ≈ 14 s, τSC ≈ 432 s; MOD (40) → 26 s, 627 s; HVY (15) → 37 s, 2,730 s. Matches Table 2 for τFC; τSC lower than the fitted means.
- Max bias of the final model vs data: 1.2% (first recovery), 3.7% (second).

## Equations
Checked against PDF text (pdftotext -layout); docling garbled 6a–6c into single characters.

$$\tau_{FC}=45\,e^{-0.014\,\%D_{CP}}+9999\,e^{-0.811\,\%D_{CP}},\qquad \tau_{SC}=9999\,e^{-0.098\,\%D_{CP}}+429$$

τ in s, %D_CP in %.

## Limitations
- Cycling, n = 10, full depletion only, no independent validation.
- 9999 constants look like fitting bounds, not physiology.
- Authors say the repeated-bout slowing could not be split between the two pools.

## Use in Running Battery
- Simulator: **best available recipe for an intensity-dependent two-pool truth model.** Map %D_CP → (CS − v)/CS × 100. Walking/standing ≈ LOW, jogging ≈ MOD/HVY. Effect: recovery while jogging near CS is very slow (τSC thousands of seconds), recovery while walking is fast. This is what drives "players who keep jogging don't recharge".
- Fatigue estimator: keep one pool; optionally make τ depend on recovery speed the same way.
- Agents / claims: "recovery is faster when the player walks than when he keeps jogging" is supported in principle (cycling lab), consistent with Skiba-type models.
- Overlay / UI: "recharging" indicator could show faster recharge during stoppages / walking.

## Ideas or questions it raised
- Test whether the simulator truth with these τ's reproduces Leifsson2024's post-peak curve.
