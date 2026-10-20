# Jones2017: The critical power concept for intermittent high-intensity exercise (review)
Citation: Jones AM, Vanhatalo A (2017). The 'critical power' concept: applications to sports performance with a focus on intermittent high-intensity exercise. Sports Medicine 47(Suppl 1):S65–S78. doi:10.1007/s40279-017-0688-0 (open access; GSSI-sponsored supplement, author received honorarium, p. S77)
Type: review (narrative)
Context: Summarises lab studies (mostly cycling and knee-extension, small samples of recreational subjects) and one analysis of 12 elite marathon runners. No football data. No team-sport CS / D′ values.
Evidence strength: medium as a summary of the CP/W′bal physiology (by the group that built the model); low for direct football numbers (none given). Narrative review, not systematic.

## Definitions and thresholds
- CP: asymptote of the power-time hyperbola; highest power sustainable without progressively drawing on W′; boundary between heavy and severe domains; occurs at ~70–90% VO2max depending on training status; closer to maximal lactate steady state than to lactate threshold (p. S66–S67).
- W′: curvature constant (kJ); fixed amount of work above CP. Running analogues: CS (m/s) and D′ (m) (p. S66).
- Classic determination: 3–5 constant-power tests lasting ~2 to ~15 min; or 3-min all-out test (3AOT): CP = end-test power, W′ = work above end-test power (p. S65–S67).
- Recovery requires power below CP; above CP there is no net W′ recharge (p. S69–S70, S75).

## Key numbers   (each with page/table/figure)
W′ recovery kinetics:

| Finding | Value | Source in paper |
|---|---|---|
| W′ after prior exhaustive bout (Ferguson 2010): control vs after 2, 6, 15 min recovery | ~22 kJ vs 8, 14, 19 kJ (≈ 36%, 64%, 86% of control — our %) | p. S74 |
| W′ reconstitution half-time (Ferguson) | ~234 s (curvilinear, faster early) | p. S74 |
| Blood lactate clearance half-time | ~1366 s | p. S74 |
| VO2 recovery (PCr proxy) half-time | ~74 s | p. S74 |
| τ_W′ at 20 W / moderate / heavy recovery (Skiba 2012) | ~377 / ~452 / ~580 s | p. S75 |
| τ_W′ with recovery above CP | ~7056 s (no net recharge) | p. S75 |
| PCr vs W′ recovery τ, knee extension (Skiba 2015) | ~57 s vs ~334 s; W′ in 2nd bout vs PCr drop r = 0.99; modelled vs actual W′ recovery r = 0.97 | p. S76 |
| W′bal error vs actual W′ across work/rest patterns (Skiba 2014) | ~1.6 kJ on average (within ~10% of W′); W′_ACT vs ΔVO2 r = 0.79 | p. S75 |
| Field triathletes (n = 8, Skiba 2014b): W′bal at exhaustion vs minimum W′bal when task completed | 0.5 ± 1.3 kJ vs 3.6 ± 2.0 kJ (ROC: useful to flag danger of exhaustion) | p. S76 |

W′ recovery τ by work/recovery pattern (Fig. 6, p. S75; Skiba 2014; approx., read from Fig. 6 bars, mean, SD ~±70–170 s):

| Work/rest (s) | 20/5 | 20/10 | 20/20 | 20/30 | 40/30 | 60/30 |
|---|---|---|---|---|---|---|
| τ (s) | ~337 (text) | ~230 | ~212 (text) | ~260 | ~300 | ~403 (text) |

So for short work bouts (20 s) τ was ~210–340 s, shorter than the 377 s from Skiba 2012 (60/30). Football efforts are even shorter.

Other numbers:
- Intermittent protocols (Chidnok 2012, cycling): S-CPO tolerance ~384 s; tolerance up by 47%, 100%, 219% with heavy, moderate, light recovery; work above CP in S-CPO ~23 kJ (p. S71).
- Passive recovery duration (Chidnok, knee extension): 18, 30, 48 s recovery → tolerance ~304, ~516, ~847 s; PCr restoration ~2× larger at 48 vs 18 s (p. S72).
- Exhaustion then recovery at 80% LT / 90% CP / 110% CP (Coats): all completed 20 min / 2 of 6 completed 20 min, others ~10 min / only ~30 s more (p. S69–S70).
- After exhaustion, PCr at 10 min reached ~96% (passive) and ~76% (below-CP exercise) of baseline; no recovery above CP (p. S70, Fig. 3).
- CP and W′ derived from intermittent exercise: CP lower and W′ higher than from continuous tests (Morton & Billat; Chidnok) (p. S71–S72). Endurance training raises CP and tends to lower W′ (p. S69).
- Self-paced vs constant tests (Black): W′ 18.1 ± 5.7 vs 20.6 ± 7.4 kJ (n.s.); CP 265 ± 44 vs 250 ± 47 W (higher when self-paced) (p. S69). Work above CP 15.3–16.6 kJ across pacing types (Chidnok) (p. S69).
- Elite marathon (Table 1, p. S68): 12 runners, CS 5.84 ± 0.14 m/s (21.0 km/h), D′ 328 ± 104 m (224–616 m); marathon run at 96 ± 2% of CS. Gebrselassie example CS 5.91 m/s, D′ 351 m, R² = 0.9996 (Fig. 2).
- Team sports: no CS or D′ values for football or other team sports are given anywhere in the review.

## Equations     (LaTeX, with variable definitions and units; mark "checked against PDF")
Eqs. 2–3 checked against PDF page images (p. S74–S75). Eq. 1 checked against pdftotext only (operators lost there); it matches Skiba2012 Eq. 2, which was checked as an image.

Morton & Billat (Eq. 1, p. S71), $t$ = tolerable time (s), $n$ = number of complete work+rest cycles, $P_W, P_R$ = work/recovery power (W), $D_W, D_R$ = work/recovery duration (s):
$$t = n(D_W + D_R) + \frac{W' - n\left[(P_W - CP)D_W - (CP - P_R)D_R\right]}{P_W - CP}$$

W′ balance (Eq. 2, p. S74), from Skiba 2012:
$$W'_{BAL} = W' - \int_0^t W'_{exp}\, e^{-\frac{t-u}{\tau_{W'}}}\,du$$

Time constant (Eq. 3, p. S75): $\tau_{W'} = 546 \cdot e^{-0.01\,D_{CP}} + 316$, with $D_{CP} = CP - P_R$ (W), τ in s.

Skiba 2015 alternative (described in words only, p. S76; not written as an equation): τ_W′ = initial W′ / (CP − P_R). In LaTeX: $\tau_{W'} = \dfrac{W'_0}{D_{CP}}$ (units J / W = s). Running analogue (OUR adaptation): $\tau_{D'} = D'_0 / (CS - v_R)$ (m / (m/s) = s).

Linear CP form (Fig. 1b): work $= CP \cdot t + W'$; distance $= CS \cdot t + D'$ (Fig. 2).

## Limitations
- Recovery kinetics "highly variable between individuals" (abstract, p. S65, S76); an algorithm needs personal CP, W′ and τ (p. S76).
- CP itself may fall and τ may change as fatigue develops (slower PCr kinetics late in sessions); not yet in the W′bal model (p. S74, S77).
- Exercise can continue briefly above CP after "exhaustion" → tolerance depends on rate of W′ use, not only its size; a 3-parameter model (with max instantaneous power) may be better (p. S70).
- No biexponential W′ recovery is fitted in this review; recovery is described as curvilinear/exponential and "faster early than late" (p. S74). Two-compartment idea is in Skiba2012 Eq. 5 only.
- All evidence is cycling / knee extension, small samples.

## Use in Running Battery
- Simulator: the Ferguson numbers (W′ back to ~36%, ~64%, ~86% after 2, 6, 15 min) give a target recovery curve for the hidden truth; a fast (PCr-like, τ ~ 57 s) plus slow (W′-like, τ ~ 334 s) two-compartment truth is well grounded here.
- Fatigue estimator: τ default range 200–580 s from cycling; shorter (~210–340 s) for short work bouts (Fig. 6). The Skiba 2015 form τ = D′/(CS − v) is a parameter-free alternative (our adaptation). Keep "no recharge when v > CS".
- Agents / claims: supported: "the authors of the model suggest it could monitor team-sport players via GPS (speeds relative to CS) to inform substitutions" (p. S76) — a proposal, not a validated use. Field evidence: W′bal near 0 coincided with exhaustion in 8 triathletes (cycling).
- Overlay / UI: show W′/D′ "battery" with a confidence band, because τ varies a lot between people.

## Ideas or questions it raised
- READING_LIST says "Justifies critical power/speed for intermittent sports. Limits of the model." Fair, but note the justification is from lab cycling intermittent protocols; the football application is only suggested (p. S76), with no football data or CS/D′ values.
- Ask: is the D′bal τ in football closer to the short-bout values (~200–300 s)? Compare with Leifsson2024 / Schimpchen2020 (high-speed running back to baseline in ~3–5 min after a peak). A τ of ~60–100 s from τ = D′/(CS − v) would fit those curves better — worth testing.
- CP/CS from intermittent work is LOWER and W′/D′ HIGHER than from continuous tests (p. S71–S72). This matches Mizelman2024's low CS from match data.

Conversion quality: partial — text good, but Eqs. 1–3 dropped from the md (only variable definitions remain); Table 1 and figure values fine in pdftotext.
