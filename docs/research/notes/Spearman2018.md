# Spearman2018: Beyond Expected Goals (potential pitch control field + off-ball scoring opportunity)
Citation: Spearman W (2018). Beyond Expected Goals. MIT Sloan Sports Analytics Conference, 2018 Research Papers Competition. (No DOI.)
Type: method (conference paper, methods only)
Context: Hudl data, 58 matches between teams of an unnamed 14-team professional league, season 2017/18, anonymised (teams A–N). Event data plus tracking of all players at 25 Hz (PDF p. 2). 5 matches for fitting, 53 for testing (pp. 10, 11). Ball tracking is not needed: on-ball events identify who has the ball (p. 3).
Evidence strength: low–medium. Conference paper with Bayesian (MAP) fitting on only 5 matches, and event timestamps with ~3 s noise (p. 3). The control part (PPCF) is the standard pitch-control formulation used later by daSilva2025 and the Friends-of-Tracking code.

## Definitions and thresholds
| Term | Definition | Source |
|---|---|---|
| OBSO | Off-ball scoring opportunity: probability that the attacking team scores with the next on-ball event, split by pitch location | pp. 2–4 |
| T_r (transition) | Probability that the next on-ball event happens at point r | p. 4 |
| C_r (control) | Probability that the passing team controls a ball at r | p. 4 |
| G_r / S_r (score) | Probability of scoring from r if the next event is there (includes chance a shot is taken) | p. 4 |
| PPCF | Potential pitch control field: per-player control probability at each point, with ball flight time and a "best-case" pass choice | pp. 4–5 |
| τ_exp(t, r) | Expected time for player j to reach r from position r_j(t) with velocity v_j(t), accelerating at constant a up to max speed v | p. 6 |
| Offside | Offside attackers get λ = 0 | p. 7 |
| Preprocessing | Least-squares smoothing for velocity and acceleration; rotate so home team attacks left to right; naive event–tracking sync by timestamp | pp. 2–3 |

## Key numbers   (each with page/table/figure)
| Item | Value | Source |
|---|---|---|
| Player max speed v | **5 m/s (18 km/h)**, same for all players ("average sustainable speed") | p. 6 |
| Player acceleration a | **7 m/s²**, constant, same for all players | p. 6 |
| Per-player v and a | Allowed in principle (footnote 3), not done | p. 6 |
| Reaction time | **Not in the model** | — |
| Event-time noise | ≈ 3 s | p. 3 |
| Frames needed | One per on-ball event, ≈ 1,000 per match (the paper says this replaces "~8,000,000 (25 Hz for 90 minutes)"; 25 Hz × 90 min is actually 135,000 frames, so that figure looks wrong or counts something else) | p. 3 |
| Mean displacement between on-ball events | SD 14 m (Fig. 3) | p. 7 |
| Example OBSO | 1.1% for the next touch (Fig. 5); match examples 2.31–3.51% (Fig. 6) | pp. 9, 12 |
| Match example | Team I vs Team D, integrated OBSO 1.32 vs 1.47, final 1–1 | p. 13 |
| Team goals/match vs OBSO/match | Pearson r = 0.76 (14 teams, 53 games) | Fig. 8, p. 14 |

Fitted parameters, Table 1 (MAP with normal priors; PDF p. 10):
| Parameter | MAP | Units | Meaning | Prior (μ, σ) |
|---|---|---|---|---|
| s | 0.54 | s | Arrival-time uncertainty (logistic) | 0.5, 0.1 |
| λ | 3.99 | s⁻¹ ("Hz") | Control rate (1/mean time to control) | 4.2, 2.0 |
| κ | 1.72 | — | Defender control-rate multiplier | 1.5, 0.5 |
| σ (transition) | 23.9 | m | Width of the 2D normal for the next-event location | 14, 10 |
| α | 1.04 | — | Weight of PPCF in pass choice | 1, 0.2 |
| β | 0.48 | — | Shape exponent of the score model | 0.5, 0.5 |

Correlation with next-match values per player (Table 2, p. 11; 53-game test set):
| Current \ next | OBSO | Shots | Goals |
|---|---|---|---|
| OBSO | 0.60 | 0.37 | 0.26 |
| Shots | — | 0.35 | 0.17 |
| Goals | — | — | 0.12 |

Top players by OBSO/match: mostly centre forwards, 0.23–0.44 per match (Table 3, pp. 14–15).

Compute cost: not reported. Only the frames-per-event remark above.

## Equations     (LaTeX; checked against PDF page images, pp. 4–10)
Total scoring probability, Eqs. (1)–(2):
$$P(G \mid D) = \sum_{r \in \mathbb R \times \mathbb R} P(G_r \cap C_r \cap T_r \mid D) = \sum_{r} P(S_r \mid C_r, T_r, D)\, P(C_r \mid T_r, D)\, P(T_r \mid D)$$
D = game state (positions, velocities).

PPCF differential equation, Eq. (3):
$$\frac{dPPCF_j}{dT}(t, \vec r, T \mid s, \lambda_j) = \Big(1 - \sum_k PPCF_k(t, \vec r, T \mid s, \lambda_k)\Big) f_j(t, \vec r, T \mid s)\, \lambda_j$$
(The PDF writes λ_j inside the sum; it should be λ_k.) PPCF_j = 0 while T < ball flight time to r. Integrated over T from 0 to ∞ (the text says "Integrating Equation 2"; it means Eq. 3). t = current match time; T = time from now [s].

Interception probability, Eq. (4):
$$f_j(t, \vec r, T \mid s) = \left[1 + e^{-\pi \frac{T - \tau_{\exp}(t, \vec r)}{\sqrt{3}\, s}}\right]^{-1}$$
s = 0.54 s (MAP). Same logistic as Spearman2017 Eq. (3) (σ there = s here).

Control rate, Eq. (5):
$$\lambda_i = \begin{cases} \lambda & i \in A \text{ (attackers)} \\ \kappa\lambda & i \in B \text{ (defenders)} \end{cases}$$
λ = 3.99 s⁻¹, κ = 1.72; λ_i = 0 for offside attackers.

Transition model, Eq. (6) (normalised to 1 over the pitch):
$$T(t, \vec r \mid \sigma, \alpha) = N(\vec r, \vec r_b(t), \sigma) \cdot \Big[\sum_{k \in A} PPCF_k(t, \vec r)\Big]^{\alpha}$$
$\vec r_b$ = ball position [m]; N = 2D normal with σ = 23.9 m; α = 1.04.

Score model, Eq. (7):
$$S(\vec r \mid \beta) = \big[S_d(|\vec r - \vec r_g|)\big]^{\beta}$$
S_d = scoring probability vs distance to goal from event data (Fig. 4, kernel-smoothed); $\vec r_g$ = goal position; β = 0.48.

Likelihood, Eq. (8):
$$\mathcal L(T \mid \boldsymbol\theta) = \prod_{D \in T} \begin{cases} P(G \mid D, \boldsymbol\theta) & k = 1 \\ 1 - P(G \mid D, \boldsymbol\theta) & k = 0 \end{cases}$$

Ball time of flight: simulated trajectories with aerodynamic drag and speed-dependent C_D (ref [9]). For each point, the flight time **closest to the nearest attacker's arrival** is used (favours the attack) (p. 6). No equation given.

## Limitations
- Conference paper; league unnamed; only 5 matches for fitting, with strong priors that pull the results (s, λ priors are taken from Spearman2017).
- Same v = 5 m/s and a = 7 m/s² for everyone. "Sustainable" speed, not a capacity.
- τ_exp with acceleration is described in words only, no formula.
- Ball flight is chosen in favour of attackers. Blocked passes not modelled. Long-pass difficulty only through the transition normal.
- Score model ignores defenders and goalkeeper (uses distance only). β is described as a "fudge factor" (footnote 6).
- Does not model the difficulty of crossing while running at speed (footnote 7), nor the effect of pressure or player speed on delivery (p. 16).

## Use in Running Battery
- Simulator: the transition model (2D normal around the ball, SD 14 m raw, σ = 23.9 m fitted, weighted by PPCF^α) is a simple, physically sensible way to pick the next event location in the synthetic event layer. The PPCF can decide who wins contested balls.
- Fatigue estimator: the PPCF has explicit v and a. That is where a fatigue-reduced top speed and acceleration plug in. Footnote 3 itself suggests per-player v and a.
- Agents / claims: OBSO lets an agent say "the tired full-back left a zone where the opponent had an x% scoring opportunity". This is model output. It must be labelled as such, and is only meaningful with the context checks.
- Overlay / UI: PPCF shading per team. Optional OBSO "danger" map.

## Ideas or questions it raised
- READING_LIST lists this as "Pitch control. Extract: formulation". Correct, but note that the PPCF parameters differ from Spearman2017: s = 0.54 s (not 0.45), λ = 3.99 s⁻¹ (not 4.3), plus κ = 1.72 and an acceleration term (7 m/s²). The common open-source version (Laurie Shaw, used by daSilva2025) mixes the two: 2017 values (σ 0.45, λ 4.3), κ = 1, λ_GK = 3λ, a reaction time of 0.7 s that neither Spearman paper has, no acceleration, and a constant 15 m/s ball.
- Spearman2018's own point (only one frame per event is needed) is useful for us. We do not need to compute pitch control on every 10 Hz frame, only at events or "moments" the agents inspect.
- Question: should we use κ = 1.72 (defender advantage)? It changes absolute PC values a lot. For comparability with daSilva2025 use κ = 1. Keep κ as a config switch.

Conversion quality: partial. Body text is good. Equations 1–8 are missing or garbled in the .md. **Table 1 is column-shifted and duplicated** in the .md (the MAP values sit under "Parameter"). All values above taken from the PDF page images.
