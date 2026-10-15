# Fernandez2018: Wide Open Spaces (Gaussian player-influence pitch control, space occupation and generation)
Citation: Fernández J, Bornn L (2018). Wide Open Spaces: A statistical technique for measuring space creation in professional soccer. MIT Sloan Sports Analytics Conference, 2018 Research Papers Competition. (No DOI; the PDF has no year on the title page. The 2018 SSAC banner is on every page.)
Type: method (conference paper, methods only)
Context: Spanish football. (1) Pitch-value neural network: Metrica Sports tracking from 20 matches of the Spanish 1st division and Segunda B, 2.4 million examples (PDF p. 8). (2) Case study: one LaLiga match, FC Barcelona vs Villarreal, January 2017, 1–1, Metrica Sports optical tracking (p. 12). Sampling rate not reported. 845 Barcelona on-ball situations analysed (p. 12).
Evidence strength: low. Conference paper. Pitch-control parameters are set by expert opinion, not fitted. There is no ground truth for space (the authors say so, p. 12). Results come from one match, checked by video with two FC Barcelona analysts.

## Definitions and thresholds
| Term | Definition / value | Source |
|---|---|---|
| Player influence I_i(p, t) | Bivariate normal PDF at location p, divided by its value at the player's current location p_i(t) | p. 4, Eqs. 1, 12–13 |
| Influence radius R_i(t) | 4 m (at the ball) to 10 m (far from ball), a function of distance to the ball D_i(t) chosen by expert analysts | p. 18, Fig. 9 |
| R(D) shape | Rises smoothly from 4 m at D = 0 to 10 m at D ≈ 18–19 m, then flat at 10 m (approx., read from Fig. 9). **Exact formula not given** | p. 19, Fig. 9 |
| "Maximum possible speed" | 13 m/s (46.8 km/h), only used to normalise speed in the stretch factor | p. 18 |
| Mean shift | Distribution centre moved ahead by half the velocity vector (0.5 s of running) | p. 19, Eq. 21 |
| Team pitch control | Logistic of (sum of own players' influence − sum of opponents' influence) | p. 5, Eq. 2 |
| Lone player | Controls logistic(1) = 0.73 at his own location | p. 5 |
| Active occupation | Player moves to the space faster than jogging, > 1.5 m/s (5.4 km/h) | p. 11 |
| Passive occupation | ≤ 1.5 m/s | p. 11 |
| Closeness δ | 5 m (average minimum distance of an opponent to the ball carrier) | p. 12 |
| Minimum attraction distance α | 3 m | p. 12 |
| Time window w | 3 s after each controlled possession | p. 12 |
| Gain threshold ε | Used, value **not given** | pp. 10–11 |
| Pitch-value grid | 21 × 15 cells; situations at least 3 s apart | p. 8 |
| Pitch-value NN | Feed-forward, 1 hidden layer, sigmoid activation, Adam, MSE loss, 10-fold CV; targets capped at 1 | pp. 7–8 |

## Key numbers   (each with page/table/figure)
| Item | Value | Source |
|---|---|---|
| Example in Fig. 2b | Player 15 m from the ball, running 6.36 m/s (22.9 km/h) at 45° | p. 5 |
| Barcelona situations | 845 (3 s windows) | p. 12 |
| Share of SOG by Iniesta, Busquets, Messi | > 41% | p. 12 |
| Messi | 66.67% of his SOG passive; 71% of his gains in front of the ball (text); Table 1: 58 in front, 23 behind | pp. 12–13 |

Space Occupation Gain, FC Barcelona vs Villarreal (Table 1, p. 13; selected rows):
| Player | # SOG | Σ SOG | μ SOG | Active % | Passive % | Front | Behind | Mean ball distance (m) | Mins |
|---|---|---|---|---|---|---|---|---|---|
| Iniesta | 96 (14.8%) | 15.77 | 0.16 | 56.25 | 43.75 | 49 | 47 | 15.19 | 94.86 |
| S. Busquets | 90 (13.9%) | 14.85 | 0.16 | 47.78 | 52.22 | 44 | 46 | 16.65 | 94.86 |
| Messi | 81 (12.5%) | 14.72 | 0.18 | 33.33 | 66.67 | 58 | 23 | 17.50 | 94.86 |
| Suárez | 70 (10.8%) | 12.27 | 0.18 | 57.14 | 42.86 | 57 | 13 | 13.46 | 94.86 |
| S. Roberto | 51 (7.8%) | 7.34 | 0.14 | 78.43 | 21.57 | 25 | 26 | 25.10 | 94.86 |
| Piqué | 29 (4.4%) | 4.92 | 0.17 | 48.28 | 51.72 | 6 | 23 | 21.05 | 94.86 |
| Digne | 26 (3.2%) | 3.48 | 0.13 | 80.77 | 19.23 | 13 | 13 | 16.23 | 71.54 |
Full backs occupy space mostly actively (78–81%) and far from the ball (p. 12).

Space generation and loss (Table 2, p. 14; selected rows):
| Player | # Generated | # Received | Σ SGG | # SOL | Σ SOL |
|---|---|---|---|---|---|
| Neymar | 28 (18.9%) | 6 (4.1%) | 5.97 | 51 | −8.53 |
| Suárez | 25 (16.9%) | 18 (12.3%) | 5.60 | 52 | −9.12 |
| Messi | 22 (14.9%) | 24 (16.4%) | 4.32 | 68 | −11.61 |
| S. Busquets | 15 (10.1%) | 24 (16.4%) | 3.83 | 38 | −6.16 |
| Iniesta | 13 (8.9%) | 21 (14.4%) | 2.62 | 75 | −11.79 |
(Table 2 lists A. Gomes as "18 (1.2%)" received, which looks like a typo.)

Compute cost: not reported. The model is closed form (one Gaussian per player per grid point, no time integration), so it is much cheaper than Spearman's (our assessment, not the paper's).

## Equations     (LaTeX; checked against PDF page images, pp. 4–5, 18–19)
Influence, Eqs. (1)/(13):
$$I_i(p, t) = \frac{f_i(p, t)}{f_i(p_i(t), t)}$$

Bivariate normal, Eq. (12):
$$f_i(p, t) = \frac{1}{\sqrt{(2\pi)^2 \det COV_i(t)}} \exp\!\Big(-\tfrac{1}{2}\big(p - \mu_i(\vec s_i(t))\big)^{T} COV_i(t)^{-1} \big(p - \mu_i(t)\big)\Big)$$
p = pitch location [m]; μ_i = mean [m]; COV_i = covariance [m²].

Covariance from rotation and scaling, Eqs. (14)–(17), (20):
$$\Sigma = V L V^{-1} = R S S R^{-1}, \quad R = \begin{bmatrix} \cos\theta & -\sin\theta \\ \sin\theta & \cos\theta \end{bmatrix}, \quad S = \begin{bmatrix} s_x & 0 \\ 0 & s_y \end{bmatrix}$$
$$COV_i(t) = R(\theta, t)\, S_i(t)\, S_i(t)\, R(\theta_i(t), t)^{-1}$$
θ = direction of the velocity vector [rad].

Speed ratio, Eq. (18):
$$Srat_i(s) = \frac{s^2}{13^2}$$
s = player speed [m/s]; 13 m/s = assumed maximum speed.

Scaling matrix, Eq. (19):
$$S_i(t) = \begin{bmatrix} \frac{R_i(t) + R_i(t)\, Srat_i(\vec s_i(t))}{2} & 0 \\ 0 & \frac{R_i(t) - R_i(t)\, Srat_i(\vec s_i(t))}{2} \end{bmatrix}$$
R_i(t) = influence radius [m], 4–10 m from distance to ball (Fig. 9). Standing player: SD = R/2 in both directions (2–5 m). Moving player: stretched along the run, squeezed across it.

Mean, Eq. (21):
$$\mu_i(t) = p_i(t) + \vec s_i(t) \cdot 0.5$$
$\vec s_i$ = velocity [m/s]; 0.5 has units of s.

Team pitch control, Eq. (2):
$$PC(p, t) = \sigma\Big(\sum_i I_i(p, t) - \sum_j I_j(p, t)\Big)$$
σ = logistic function; i = players of the team, j = opponents. An extra constant inside σ is optional (p. 6).

Pitch value, Eqs. (3)–(5):
$$V_{k,l}(t) = fn(p_b(t), p_{k,l}(t); \theta), \quad D_{k,l}(t) = \sum_d I_d(p_b(t), p_{k,l}(t)), \quad \hat V_{k,l}(t) = \min(1, D_{k,l}(t))$$
Fitted by MSE with a 1-hidden-layer NN, then multiplied by a [0, 1] distance-to-goal surface (p. 9).

Space quality and gains, Eqs. (6)–(11):
$$Q_i(t) = PC_i(t)\, V(t), \qquad G_i(t) = \frac{\sum_{t'=t+1}^{t+w+1} Q_i(t')}{w}$$
$$SOG_i = G_i \text{ if } G_i \ge \epsilon \text{ else } 0, \qquad SOL_i = -G_i \text{ if } G_i \le -\epsilon \text{ else } 0$$
$$SG_{i,i'}(t) = \exists j:\ (d_{i',j}(t) \le \delta) \wedge (d_{i,j}(t+w) \le \delta) \wedge (d_{i',j}(t+w) > \delta) \wedge (d_{i,j}(t+w) - d_{i,j}(t) < \alpha)$$
SGG = G_j when SG holds and G_j ≥ ε. (Eq. 7 is called a "mean difference" in the text but is written as a mean.)

## Limitations
- Parameters (4–10 m radius, the R(D) curve, 13 m/s, the 0.5 s shift) come from expert opinion. Nothing is fitted to outcomes such as who actually wins the ball.
- No ground truth for space; validation by video only; one match.
- **No top-speed, acceleration or reaction parameter.** The model uses only current position, current velocity and distance to the ball. Speed only stretches and shifts the Gaussian. A player's capacity (how fast he could run) does not appear.
- The R(D) function is shown only as a figure.
- Our observation: I_i is normalised by the PDF value at the player's current position, but the Gaussian is centred 0.5·s ahead. For a moving player, I_i is therefore > 1 near μ_i, so "within [0, 1]" (p. 4) holds only for a standing player.
- The 13 m/s "maximum speed" is not a realistic human value (world-class sprinters peak ≈ 12 m/s). It is only a scale constant.
- Sampling rate, ε and compute cost not reported.

## Use in Second Wind
- Simulator: not needed for generation. The SOG/SGG thresholds (active > 1.5 m/s, δ = 5 m, α = 3 m, w = 3 s) could tag synthetic "space creation" moments if we want them.
- Fatigue estimator: poor fit. The only way to add fatigue is ad hoc (for example, cap the speed used in Srat and the mean shift, or shrink R). Nothing published supports those changes. Spearman's time-to-intercept has v_max directly and is the better choice.
- Agents / claims: SOG/SOL language ("lost 3 s of space occupation") is attractive for fans, but the evidence base is one match.
- Overlay / UI: cheap and smooth control maps for every 10 Hz frame. Fine for a "visual only" background layer if Spearman PC is too slow to run per frame, provided we do not claim it reflects fatigue.

### Comparison with Spearman (our assessment)
| | Spearman 2017/2018 (Shaw variant used by daSilva2025) | Fernández & Bornn 2018 |
|---|---|---|
| Per grid point | Time-to-intercept for 22 players, then numerical ODE integration (dt 0.04 s, ~tens of steps until convergence) | 22 closed-form Gaussian evaluations + 1 logistic |
| Parameters fitted to data | Yes (σ, λ by max likelihood on 5–11 matches) | No (expert-set) |
| Physical meaning | Arrival time, control rate | Heuristic influence |
| Top speed / acceleration | Explicit (v_max; a in 2018) | Absent |
| Fatigue hook | Replace v_max with ξ·v95 (daSilva2025 did exactly this) | None without inventing a rule |
| Simplicity to code | Medium | Simple |
| Cost per frame | Higher (roughly 10–100× more work per grid point, our estimate) | Low |
Verdict: Fernández is simpler and cheaper to implement. Spearman is the only one where a fatigue-reduced top speed (and acceleration) has a clear, published place.

## Ideas or questions it raised
- READING_LIST: "Alternative pitch control. Pick the simpler of the two." Fernández is simpler, but it cannot carry the fatigue effect, which is the reason we need pitch control at all. So "the simpler" is the wrong selection rule here. Pick Spearman (Shaw/da Silva variant) for the fatigue story.
- If speed is an issue, a hybrid is possible: Fernández for the live background shading, Spearman with fatigue for the "moments" the agents explain. That risks two maps disagreeing on screen, so it is probably better to use Spearman on a coarse grid at low frame rate.

Conversion quality: partial. Body text and Tables 1–2 are fine (ligature "ﬁ" sometimes became "ϐ"). The appendix equations (12–21) and the Eq. 2 notation are missing or garbled in the .md. Fig. 9 (the R(D) curve) is only in the PDF. Equations taken from the PDF page images.
