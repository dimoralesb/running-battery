# Spearman2017: Physics-based pass probability model (time-to-intercept + time-to-control)
Citation: Spearman W, Basye A, Dick G, Hotovy R, Pop P (2017). Physics-Based Modeling of Pass Probabilities in Soccer. MIT Sloan Sports Analytics Conference, 2017 Research Papers Competition. (No DOI.)
Type: method (conference paper, methods only)
Context: Premier League 2015/16, elite men, Crystal Palace's 38 matches. Tracking (all players + ball) at 25 Hz plus event data. Provider not named (authors are at Hudl). 11 matches to train, 12 to test, all 38 for applications. 10,875 passes after filtering (5,404 train, 5,471 test) (PDF p. 6).
Evidence strength: low–medium. Conference paper, not peer-reviewed in a journal. One team's matches. But the model is fitted by maximum likelihood on real passes and tested out of sample. It is the base of most later pitch-control work.

## Definitions and thresholds
| Term | Definition | Source |
|---|---|---|
| Controlled touch | Any on-ball action showing control. Events used: pass, tackle, claim, ball recovery, keeper pick-up (aerial duels not counted) | PDF pp. 2, 6 |
| Receiver | Next player (not the passer) to make a controlled touch | p. 2 |
| Successful pass | Receiver is on the passer's team | p. 2 |
| Time to intercept t_int | Shortest time for a player to reach a point on the ball path, given position, velocity, max speed and max acceleration | p. 3 |
| Δt | T − t_int, where T = ball flight time to that point. Δt ≥ 0 means the player can intercept | p. 3 |
| σ | Uncertainty of interception time (from different speeds, reaction times, effort levels not modelled) | p. 3 |
| λ | Control rate; 1/λ = mean time to gain control while near the ball | pp. 3–4 |
| Pass filter | Duration 0.5–10 s, track curvature < 5%, ball not going out of play | p. 6 |
| Ball initial velocity | Average of the first 10 frames of the pass (0.4 s) | p. 2 |
| Pitch control function (PCF) | Pass probability for an imaginary **stationary** ball at each pitch point (no flight time). Team PCF = sum of its players' PCFs | p. 11 |

## Key numbers   (each with page/table/figure)
| Item | Value | Source |
|---|---|---|
| σ (fitted) | 0.45 ± 0.01 (stat) ± 0.04 (syst) s. Fig. 5 caption: 0.45 ± 0.05 s | p. 7, Fig. 5 |
| λ (fitted) | 4.30 ± 0.28 (stat) ± 1.1 (syst) s⁻¹. Fig. 5 caption: 4.30 ± 1.14 s⁻¹ | p. 7, Fig. 5 |
| Meaning | ≈ 95% chance to control within the first second; most interception times within ±1 s of the computed time | p. 7 |
| **Max speed v_max, max acceleration a_max** | Used as constraints, **no values given** | p. 3, Eq. 2 |
| **Reaction time** | **Not in the model** (only mentioned as one source of σ) | p. 3 |
| Ball: g | 9.8 m/s² | p. 2 |
| Ball: mass m | 0.42 kg | p. 2 |
| Air density ρ | 1.22 kg/m³ | p. 2 |
| Drag coefficient C_D | 0.25 (constant) | p. 2 |
| Ball cross-section A | 0.038 m² | p. 2 |
| Magnus force | ignored (ball travels straight); no rolling friction; vertical velocity set to 0 at ground contact | p. 2 |
| Accuracy, receiving team (test set) | 80.5% (81.9% with cut-off 0.27 instead of 0.5) | p. 8 |
| Accuracy, exact receiver | 67.9% (73.1% in one example match) | p. 8, Fig. 6 |
| Pass completion: observed vs model mean | 78.9% observed vs 67.9% model (model under-predicts success) | p. 8 |
| Worked example (Fig. 3) | Three players: 17.8%, 56.0%, 26.2% receive probability | p. 5 |
| Value model constants (Eq. 12) | a = 0.93, b = 0.14, c = 0.02 | p. 10 footnote 2 |
| Correlations (Pearson, team level) | reception efficiency vs shots 0.64, vs passes in final third 0.70; mean pass value vs shots 0.63, vs final-third passes 0.83 | p. 10 |

Receiving efficiency (actual / expected receptions) by position, Table 1 (p. 9):
| Position | Total | Receiving (teammate passes) | Interception (opponent passes) |
|---|---|---|---|
| Defender | 1.06 ± 0.03 | 1.04 ± 0.03 | 1.13 ± 0.06 |
| Midfielder | 1.03 ± 0.02 | 1.23 ± 0.03 | 0.57 ± 0.03 |
| Forward | 0.91 ± 0.03 | 1.36 ± 0.06 | 0.23 ± 0.02 |
| Goalkeeper | 0.65 ± 0.05 | 0.80 ± 0.07 | 0.48 ± 0.06 |

Corner kicks, mean defending-team PCF within radius r of goal (Table 3, pp. 11–12):
| Radius | 5 m | 10 m | 15 m | 20 m | 25 m |
|---|---|---|---|---|---|
| Saved shot | 0.82 | 0.75 | 0.68 | 0.62 | 0.53 |
| Goal | 0.79 | 0.74 | 0.67 | 0.61 | 0.53 |
Defenders hold ≈4% less control within 5 m when a goal is scored. Small difference, no test.

Compute cost: not reported, except that hypothetical-pass search (simulated annealing) is too slow for large-scale use (p. 13).

## Equations     (LaTeX; checked against PDF page images, pp. 2–5, 7, 9–10)
Ball motion, Eq. (1):
$$\ddot{\vec r} = -g\hat z - \frac{1}{2m}\rho C_D A\, |\dot{\vec r}|\, \dot{\vec r}$$
$\vec r$ = ball position [m]; g = 9.8 m/s²; m = 0.42 kg; ρ = 1.22 kg/m³; C_D = 0.25; A = 0.038 m².

Player motion, Eq. (2):
$$\vec r = \vec r_i + \dot{\vec r}\, t + \tfrac{1}{2}\ddot{\vec r}\, t^2, \qquad |\dot{\vec r}| \le v_{\max},\ |\ddot{\vec r}| \le a_{\max}$$
Solved for the smallest t = t_int with $\vec r(t_{\text{int}}) = \vec r_{\text{ball}}(T)$; so t_int = f_int(T). $\vec r_i$ = start position [m]. The paper gives no closed form and no values for v_max, a_max.

Interception probability, Eq. (3) (logistic CDF; σ² is the variance of the logistic, footnote 1):
$$P_{\text{int}}(T) = \frac{1}{1 + e^{-\frac{T - t_{\text{int}}}{\sqrt{3}\,\sigma/\pi}}} = \frac{1}{1 + e^{-\frac{T - f_{\text{int}}(T)}{\sqrt{3}\,\sigma/\pi}}}$$
T = ball flight time to the point [s]; σ = 0.45 s.

Time to control, Eq. (4):
$$P(t) = 1 - e^{-\lambda t}$$
λ = 4.30 s⁻¹.

Receive probability, Eqs. (5)–(6):
$$\frac{dP_j}{dT}(T) = \Big(1 - \sum_k P_k(T)\Big) P_{\text{int},j}(T)\, \lambda$$
$$P_j(t) = \int_0^t \Big(1 - \sum_k P_k(T)\Big) P_{\text{int},j}(T)\, \lambda\, dT$$
Integrated numerically for all players at once, t → ∞. Pass success $P_A = \sum_{j \in A} P_j$ (A = passer's teammates, passer excluded).

Fit, Eqs. (7)–(9): Bernoulli likelihood per pass; grid search minimising $-\sum_{i \in P} \log \mathcal L(\sigma, \lambda \mid k_i, x_i)$.

Aggregation, Eq. (10): $\mu = \sum_i p_i$, $\sigma^2 = \sum_i (1 - p_i) p_i$ (Poisson binomial).

Pass value, Eqs. (11)–(12):
$$V_j = p_j f(x_{\text{suc}}) - (1 - p_j) f(x_{\text{fail}}), \qquad f_{\text{simple}} = a\, e^{-b\sqrt{(\vec r_{\text{target}} - \vec r_{\text{ball}})^2}} + c$$
a = 0.93, b = 0.14 (per m), c = 0.02.

## Limitations
- Conference paper; one club's matches (Crystal Palace); tracking provider not named.
- The key physical parameters (v_max, a_max) are not reported, so the fitted σ and λ are tied to unknown speed/acceleration values.
- All players share the same v_max, a_max, σ, λ (no individual or fatigue terms).
- The model under-predicts completed passes (67.9% vs 78.9%), probably from missing intent, spin and tactics (p. 8).
- No reaction time, no κ (defender advantage), no offside rule in this version.
- The pitch-control extension ignores ball flight time (stationary ball).

## Use in Running Battery
- Simulator: σ = 0.45 s and λ = 4.3 s⁻¹ can drive a simple "who wins the loose ball / pass" rule in the event layer, so outcomes follow from positions and speeds (including fatigue-reduced speeds). Ball drag constants (Eq. 1) give realistic ball flight if we model it.
- Fatigue estimator: not directly. A fatigue-reduced v_max (and a_max) enters Eq. 2, which is the natural hook for "slower to get there".
- Agents / claims: allowed: "the model gives an x% chance he would have got there first". Back it with the model, not with fatigue evidence.
- Overlay / UI: pass-probability lines and pitch-control shading. Per-position interception efficiency (Table 1) shows defenders intercept above expectation, forwards far below. Context for the narrator.

## Ideas or questions it raised
- READING_LIST says "time-to-intercept with reaction time, top speed, acceleration" and asks for "default parameters". **Imprecise:** this paper has no reaction time and gives no values for top speed or acceleration. Only σ = 0.45 s and λ = 4.30 s⁻¹ are given. The often-quoted 5 m/s and 7 m/s² come from Spearman2018 (p. 6). The 0.7 s reaction time comes from Laurie Shaw's Friends-of-Tracking code (cited by daSilva2025 as ref 28), not from any Spearman paper.
- Because σ was fitted with unknown v_max/a_max, reusing σ = 0.45 s with the Shaw TTI (reaction + constant speed) is a convention, not a refit.
- With synthetic data, we could refit σ and λ on our own simulated passes to check the simulator's pass outcomes are physically consistent.

Conversion quality: partial. Text and Tables 1–3 are fine. **All equations (1–6, 9–12) are missing or garbled** in the .md (for example "𝑟 ≤ 𝑣max" lost the derivative dots). Equations taken from the PDF page images.
