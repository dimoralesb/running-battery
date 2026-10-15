# Bellenger2025: Does end-of-session D′ balance identify exhausting interval runs?
Citation: Bellenger CR, Nitschke M, Bartram JC. Validation of end-of-session D′ balance for quantifying and differentiating exhaustive and nonexhaustive intermittent-training sessions in runners. Int J Sports Physiol Perform 2025;20(5):718–726. doi:10.1123/ijspp.2024-0036
Type: field study (secondary analysis)
Context: 6 highly trained / national-level endurance runners (5 M, 1 F; 25.3 ± 7.1 y), Australia, Nov 2021–Mar 2022. 30 interval sessions (14 exhaustive, 16 not, rated by the coach): 200–1600 m efforts at ~105–130% of CS, 45–180 s passive or active recovery. Personal GPS watches (TrainingPeaks export). CS and D′ from season-best 1500/3000/5000 m.
Evidence strength: low-medium. Tiny n, endurance runners (not footballers), coach-rated exhaustion, the individual-τ analyses are exploratory (n = 4–8 sessions). But it is **the only running-specific test of speed-based D′ balance** we have. (Full 9-page PDF; an earlier copy was a 2-page preview.)

## Definitions and thresholds
- Depletion: D_bal = D′(start) − (S − CS)·u. Recovery: D_bal = D′ − (D′ − D′(start))·e^(−u/τ), with **Skiba's τ = D′/D_CS**, D_CS = CS − recovery speed (p.719–720, checked against PDF text).
- Individual τ: for one exhaustive, passive-recovery session per athlete, τ was solved so that D_bal = 0 at the end; then applied to the athlete's other 24 sessions (p.720).
- CS and D′ from the linear speed vs 1/time fit of race bests.

## Key numbers   (each with page/table/figure)
- Runner parameters (Table 1, p.719): **CS 5.12 ± 0.39 m/s (18.4 km/h), D′ 274 ± 54 m**; SEE of CS 1.2%, of D′ 9.1 ± 6.5% (max 20.4%).
- **Skiba τ (standard model):** end-of-session D_bal 157 ± 25 m (**60 ± 7% of D′**) in exhaustive vs 200 ± 19 m (73 ± 5%) in non-exhaustive sessions; ES 1.01, p = .01; 95% CI 132–181 m excludes 0; ROC AUC 0.79; with a 25 m (~10%) exhaustion threshold, **0 sessions classified correctly** (p.721–722; Fig. 2a, 3a).
- **Individual τ:** 16 ± 20 m (7 ± 8%) vs 100 ± 20 m (38 ± 9%); ES 2.43, p < .001; CI −5 to 36 m includes 0; **AUC 0.97; at 25 m, 75% of exhaustive and 100% of non-exhaustive sessions classified correctly**. Passive-recovery sessions only: 9 ± 38 m vs 100 ± 23 m, AUC 0.94 (p.722; Fig. 2b–c, 3b–c).
- **Recovery time constants: individual τ 250–649 s (mean 362 ± 148 s) at D_CS 4.09 ± 0.45 m/s (passive recovery), vs Skiba-derived τ 53–94 s (mean 68 ± 17 s)**: the standard running τ is about **5× too fast** (p.722; Fig. 4a).
- At the same relative recovery intensity, runners' τ were slower than modelled τ for elite cyclists (Skiba and Bartram equations) (Fig. 4b).
- Example session (Fig. 1): end-of-session D_bal 122 m with Skiba τ vs 15 m with individual τ.

## Equations
Skiba 2015 depletion/recovery in speed form, as above. Checked against PDF text (pdftotext).

## Limitations
- 6 runners; individual τ fitted on one session each and assumes exhaustion = exactly 0 and race-derived CS/D′ are right for training days. The fitted τ also absorbs any error in CS and D′.
- Exhaustion is the coach's judgement.
- Active recovery (~30% of D_CS) was treated with the passive τ (trivial effect here, ES 0.19).
- Authors suggest the τ = D′/D_CS scaling may be wrong for running (1 W ≠ 1 m/s), or running recovers slower than cycling (more muscle mass, slower autonomic recovery) (p.722–725).

## Use in Second Wind
- Simulator: in the truth model the **slow** recovery pool should have τ of minutes (≈ 250–650 s at rest), not about one minute.
- Fatigue estimator: **the standard running τ = D′/(CS − v) recovers far too fast for runners.** With it, the battery stays near full (here ~60% at real exhaustion; Sutcliffe2025 saw a deepest dip of only ~21% in university football). Add a running correction factor k: τ = k·D′/(CS − v), with k ≈ 5 from this paper (≈ 360 s at rest), and test k = 1, 3, 5. With the right τ, D′ balance discriminated exhausting sessions very well (AUC 0.97).
- Agents / claims: keep "battery is a relative gauge" ("lowest of his match", "lower than teammates"). Never "exhausted" from the battery, because the right τ for football is unknown.
- Overlay / UI: with k ≈ 5 the battery visibly drains during hard spells and refills over minutes, which also reads better on screen.

## Ideas or questions it raised
- Two timescales fit everything: behaviour after a peak returns within ~2–5 min [Leifsson2024] (fast processes), while the D′ battery refills over ~6 min or more (slow). Our model already separates these: §3.4 post-peak module (fast, empirical) and §3.2 battery (slow).
