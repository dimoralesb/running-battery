# Skiba2012: The W′ balance (W′bal) model
Citation: Skiba PF, Chidnok W, Vanhatalo A, Jones AM (2012). Modeling the expenditure and reconstitution of work capacity above critical power. Medicine & Science in Sports & Exercise 44(8):1526–1532. doi:10.1249/MSS.0b013e3182517a80
Type: lab study (cycling, mathematical model) + one field case
Context: 7 healthy recreationally active (not highly trained) males, 26 ± 5 yr, 1.79 ± 0.06 m, 81 ± 6 kg; cycle ergometer (Lode Excalibur Sport), University of Exeter (p. 1527). Data from the companion study Chidnok et al. 2012. Field case: one "well-trained" / "competitive amateur" cyclist, power meter data from a road race (p. 1529–1530). No running, no football, no tracking.
Evidence strength: medium for the equation's form (widely used, physiologically grounded), low for transfer to football (n = 7, cycling, lab intervals 60 s on / 30 s off, constants fitted in the same data, one-case field "validation").

## Definitions and thresholds
- CP (W): mean power in the final 30 s of a 3-min all-out cycling test. W′ (J): power-time integral above that end-test power (p. 1528).
- Protocol: 4 intermittent trials to exhaustion, each 60-s work at P6 + 50% of (P6 − CP), where P6 = power predicted to exhaust in 6 min, alternated with 30-s recovery at (p. 1528):
  1. S20: 20 W;
  2. SM (moderate): 90% of GET;
  3. SH (heavy): GET + 50% of (CP − GET);
  4. SS (severe): P6 − 50% of (P6 − CP), i.e. recovery still above CP.
- Assumptions (p. 1527): W′ expenditure starts the moment power exceeds CP; reconstitution starts the moment power falls below CP; reconstitution is exponential.
- Fitting: joules expended above CP per second entered into Eq. 3; τ_W′ varied iteratively until modelled W′bal = 0 exactly at exhaustion (p. 1528). So the lab τ values are fitted, not predicted.
- D_CP (W): difference between CP and the recovery power output (CP − P_recovery) (p. 1528).

## Key numbers   (each with page/table/figure)
Table 1 (p. 1528): W′, CP, VO2max per subject.

| | W′ (kJ) | CP (W) | VO2max (L/min) |
|---|---|---|---|
| Mean ± SD | 21.1 ± 4.7 | 240 ± 56 | 4.1 ± 0.778 |
| Range | 14.3–28 | 187–351 | 3.19–5.59 |

Table 2 (p. 1529): fitted τ_W′ (s), mean ± SD (range):

| Recovery condition | τ_W′ (s) |
|---|---|
| S20 (20 W) | 377 ± 29 (321–421) |
| SM (moderate) | 452 ± 81 (321–570) |
| SH (heavy) | 578 ± 105 (377–719) (text says 580 ± 105) |
| SS (above CP) | 7056 ± 11,169 (596–30,758) (text says ± 11,969) — non-physiological = no net recharge |

- τ_W′ vs D_CP (S20, SM, SH pooled): linear r² = 0.67, P < 0.0001; best fit exponential y = a·e^(−kx) + b, r² = 0.77; parameter SEs a = 86.11, k = 0.004, b = 61.8 (p. 1528–1529, Fig. 2). Authors note a bilinear fit would also work (Fig. 2 caption).
- τ_W′ vs CP: r² = 0.64 (P = 0.03) in SM; trends in S20 (r² = 0.53, P = 0.06) and SH (r² = 0.48, P = 0.08); none in SS (p. 1528). The subject with the highest CP (subject 4, 351 W, VO2max 5.59 L/min) had the shortest τ (321 s) and no change S20 → SM (p. 1529–1530).
- Modelled W′ expended vs rise in VO2 above baseline: r² = 0.82–0.96 (P < 0.0002–0.0049) (p. 1529, Fig. 3).
- Earlier estimate (Ferguson 2010, cited p. 1527): W′ recovery t½ ≈ 234 s, i.e. τ ≈ 336 s. PCr-based sprint power recovery τ ≈ 333 s (Bogdanis, cited p. 1530).
- Field case (p. 1529–1530, Fig. 4): CP 227 W, peak 409 W; D_CP from mean of all sub-CP power (75 W), held constant; τ = 440 s from Eq. 4. Cyclist had to drop below CP each time W′bal fell below ~1.5 kJ; retired after 55.4 min when W′ was nearly depleted. (Our arithmetic: Eq. 4 with D_CP = 152 W gives ≈ 435 s, consistent with the reported 440 s.)
- Running adaptation: the paper itself says P and CP can be replaced by speed and CS, and W′ by distance (p. 1526), and that adapting the equation to CS and distance would allow GPS-watch use in running races (p. 1531). It does NOT do this adaptation or give any running τ.

## Equations     (LaTeX, with variable definitions and units; mark "checked against PDF")
All checked against PDF page images (p. 1527, 1529, 1531).

Eq. 1, two-parameter CP model: $P = \dfrac{W'}{t} + CP$ ($P$ power W; $t$ time to exhaustion s; $CP$ W; $W'$ J).

Eq. 2, Morton & Billat intermittent model ($t$ total endurance time s; $n$ number of work+rest cycles; $P_w, P_r$ work/rest power W; $t_w, t_r$ work/rest interval durations s):
$$t = n(t_w + t_r) + \frac{W' - n\left[(P_w - CP)\,t_w - (CP - P_r)\,t_r\right]}{P_w - CP}$$

Eq. 3, W′ balance (as printed; the integrand has no explicit $du$ in the original, Jones2017 adds it):
$$W'_{bal}(t) = W' - \int_0^t W'_{exp}(u)\; e^{-(t-u)/\tau_{W'}}\,du$$
$W'$ = known W′ from the 2-parameter model (J); $W'_{exp}(u)$ = W′ expended at time $u$ (J per s; in practice $P(u) - CP$ when $P > CP$, else 0); $t - u$ = time (s) since that expenditure; $\tau_{W'}$ = time constant of reconstitution (s). Each joule spent is recharged exponentially while power is below CP.

Eq. 4, time constant vs recovery intensity (fitted on S20, SM, SH):
$$\tau_{W'} = 546\, e^{-0.01\, D_{CP}} + 316$$
$\tau_{W'}$ in s; $D_{CP} = CP - P_{recovery}$ in W (so the constant 0.01 has units W⁻¹); 546 and 316 in s. Range of $D_{CP}$ in the data ≈ 80–300 W (approx., read from Fig. 2). Limits of Eq. 4 (our arithmetic): τ → 862 s at $D_{CP}$ = 0, τ → 316 s for large $D_{CP}$; τ ≈ 390 s at $D_{CP}$ = 200 W.

Eq. 5, proposed two-compartment generalisation (no fitted values given; $k_1, k_2$ gain terms, $\tau_1, \tau_2$ time constants for type I and type II fibre "compartments"):
$$W'_{bal}(t) = W' - \int_0^t \left(k_1 e^{-(t-u)/\tau_1} + k_2 e^{-(t-u)/\tau_2}\right) w(u)\,du$$

The simpler differential form of Skiba 2015 (τ = W′/D_CP) is NOT in this paper (it is mentioned in Jones2017, citing Skiba et al. 2015).

## Limitations
- Cycling, 7 recreational males; only one work/rest pattern (60 s / 30 s). Football efforts are 2–10 s with irregular recovery.
- τ fitted by forcing W′bal = 0 at exhaustion in the same data, so it is a description, not an independent prediction. Field "prediction" is one cyclist, retrospective.
- Eq. 4 uses D_CP in watts; the constants cannot be moved to speed (m/s) by unit conversion. D_CP held constant in the field case, while in reality it changes second by second (p. 1531).
- Assumes CP and W′ stay constant during exercise; recovery above CP is undefined (τ explodes). Highly fit people may recover differently (subject 4).
- Assumes depletion is linear in (P − CP) and recharge single-exponential; authors already suggest a two-compartment model.

## Use in Second Wind
- Simulator: our hidden truth should be richer than this (e.g., two-compartment Eq. 5 with fast + slow τ, plus individual variation), so the estimator's single-τ D′bal is not tested against itself.
- Fatigue estimator: OUR ADAPTATION (not done in this paper): replace $P \to v$ (m/s), $CP \to CS$ (m/s), $W' \to D'$ (m), $W'_{exp}(u) = \max(0, v(u) - CS)$ (m per s). For τ we cannot reuse Eq. 4 directly (units W). Options: (a) a fixed τ of ~300–400 s as order of magnitude from cycling, (b) the Skiba 2015 form τ = D′/(CS − v_rec) cited in Jones2017, (c) calibrate on synthetic truth / on the post-peak recovery curves of Leifsson2024 / Schimpchen2020. State clearly in the UI that τ is an assumption.
- Agents / claims: may say "battery model based on the W′ balance model from cycling research (Skiba 2012), adapted to running speed"; must NOT say it is validated in football.
- Overlay / UI: Fig. 4-style plot (W′bal line over speed trace) is exactly our "battery" visual. The ~1.5 kJ "forced to ease off" observation suggests a "low battery" zone near empty, not at 0.

## Ideas or questions it raised
- READING_LIST says "W′bal equation and recovery time constant. We adapt power → speed (CS, D′)". Correct; just note the recovery constant (546 e^(−0.01 D_CP) + 316) is in watts and comes from cycling with 30-s recoveries — there is no running τ here.
- Quick unit idea (our own): express D_CS as a fraction of CS and map to the same τ range (≈ 320–860 s), or fit a running-specific τ curve to our synthetic or published football recovery curves.
- Abstract says exponential fit r² = 0.77 (body text agrees); abstract OCR in the md shows "0.11", a conversion error.

Conversion quality: bad — scanned PDF, OCR text is full of errors (W′ symbols, "Med. Sei."), Eqs. 3–5 missing or garbled, abstract r² shown as 0.11. Use the PDF images.
