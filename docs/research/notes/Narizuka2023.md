# Narizuka2023: Validation of the Fujimura–Sugihara motion model for sprints with tracking data
Citation: Narizuka T, Takizawa K, Yamazaki Y (2023). Validation of a motion model for soccer players' sprint by means of tracking data. Scientific Reports 13:865. DOI: 10.1038/s41598-023-27999-1 (preprint version: arXiv:2205.04511). The file in docs/papers is the published Scientific Reports version (received 12 Apr 2022, accepted 11 Jan 2023).
Type: method (validation of a physics-based motion model on tracking data); peer-reviewed journal article, not only a preprint
Context: Japan J1 League (top division), 2016 season, 54 matches, 18 teams; all outfield players pooled (goalkeepers excluded), number of players not stated. Tracking: TRACAB optical system, positions every 0.04 s (25 Hz), position error stated as ±1 m. Data from DataStadium Inc. (proprietary).
Evidence strength: medium. Large real match dataset, simple and transparent method, but parameters are a single pooled "envelope" for all players (no per-player fits), estimated from heat-map extremes that are sensitive to noise and outliers, and the fitted V_max values are not physically realistic as top speeds.

## Definitions and thresholds
- Velocity v(t): difference between current position and the position 1 s earlier (p. 2). So "speed" here is a 1-s average.
- Fujimura–Sugihara model: point mass with a driving force of fixed size F in any chosen direction n and a viscous drag k·v (Eq. 3).
- Kinetic parameters: V_max = F/k (m/s) and α = k/m (1/s). In di Prampero's notation α = 1/τ.
- Arrival circle: the set of points reachable in Δt seconds when n can point anywhere: centre A(α, Δt)·v0, radius B(α, V_max, Δt) (p. 3).
- Heat maps: for each player and time t, rotate so v(t) points along +x, plot position at t + Δt; group by initial speed in bins of Δv0 = 0.3 m/s; cell size 0.2·Δt m; isolated cells removed (cells need > c non-blank neighbours: c = 8 for Δt < 1 s, 6 for 1–3 s, 4 for > 3 s) (p. 4).
- Circle fit from heat-map extremes (Eq. 7–8).

## Key numbers   (each with page/table/figure)
Pages are journal pages (1–8 = PDF pages 1–8).

| Variable | Value | Source |
|---|---|---|
| Speed distribution peaks | ≈ 1 m/s (walking, all players) and ≈ 3 m/s (jogging, outfield only); tails decay roughly exponentially; outfield speeds up to ≈ 9.5 m/s | p. 2, Fig. 1 |
| Straight-line motion time scale | MSD ∝ τ² (straight line) up to ≈ 10 s, ∝ τ (random walk) beyond | p. 3, Fig. 2 |
| Arrival region shape | circular, not elliptical, for all v0 shown (1, 3, 5, 7 m/s) at Δt = 1 and 2 s | p. 4, Fig. 4 |
| Centre x_c vs v0 | linear for v0 ≲ 6 m/s; slope 0.58 (Δt = 1 s), 0.84 (Δt = 2 s); y_c ≈ 0 | p. 4, 6; Fig. 5 |
| Radius r_c | ≈ constant for v0 ≤ 6 m/s: 6.16 m (Δt = 1 s), 12.94 m (Δt = 2 s); drops for v0 > 6 m/s (≈ 4.8 m and ≈ 10.4 m at v0 = 8 m/s, approx., read from Fig. 6) | p. 5, Fig. 6 |
| α, V_max at Δt = 1 s | 1.23 1/s, 14.53 m/s | p. 6 |
| α, V_max at Δt = 2 s | 1.04 1/s, 11.19 m/s | p. 6 |
| Earlier lab values (Fujimura & Sugihara 2005, 3 amateur field-hockey players) | α = 1.3 1/s, V_max = 7.8 m/s | p. 3, 6 |

Δt dependence (Fig. 7, p. 6; approx., read from Fig. 7):

| Δt (s) | α (1/s) | τ = 1/α (s) | V_max (m/s) | α·V_max = start acceleration (m/s², my calc) |
|---|---|---|---|---|
| ≈ 0.2 | ≈ 2.25 | ≈ 0.44 | ≈ 24 | ≈ 54 |
| 0.5 | ≈ 1.55 | ≈ 0.65 | ≈ 18.5 | ≈ 29 |
| 1.0 | 1.23 | 0.81 | 14.53 | 17.9 |
| 1.5 | ≈ 1.13 | ≈ 0.88 | ≈ 12 | ≈ 13.6 |
| 2.0 | 1.04 | 0.96 | 11.19 | 11.6 |
| 2.5 | ≈ 0.94 | ≈ 1.06 | ≈ 10.7 | ≈ 10.1 |
| 3.0 | ≈ 0.91 | ≈ 1.10 | ≈ 10.3 | ≈ 9.4 |
| 4.0 | ≈ 0.84 | ≈ 1.19 | ≈ 10.0 | ≈ 8.4 |
| 5.0 | ≈ 0.86 | ≈ 1.16 | ≈ 9.4 | ≈ 8.1 |

Parameters are not constant: they settle at α ≈ 0.85 1/s (τ ≈ 1.2 s) and V_max ≈ 9.5–10 m/s for Δt ≥ 3–5 s, and blow up for Δt ≲ 1 s. Authors give two possible reasons: ±1 m position error (dominant at short Δt) or a real limit of the model (p. 6). No distributions across players are reported.

Check of the paper's arithmetic (my calc): A(1.23, 1) = (1 − e^(−1.23))/1.23 = 0.576 ✓; A(1.04, 2) = 0.841 ✓; V_max = r_c/(Δt − A) = 6.16/0.424 = 14.5 ✓ and 12.94/1.159 = 11.2 ✓.

## Equations     (LaTeX, with variable definitions and units; mark "checked against PDF")
All checked against PDF (pp. 3–4, 7).

Mean squared displacement (Eq. 1–2):
$$\langle|\Delta\vec x|^2\rangle_\tau \sim \tau^{\beta}, \qquad \langle|\Delta\vec x|^2\rangle_\tau = \frac{1}{T-\tau}\sum_{t=0}^{T-\tau}\left|\vec x(t+\tau)-\vec x(t)\right|^2$$
τ = lag (s); T = length of one in-play sequence (restart to stoppage); β = 2 straight line, β = 1 random walk.

Fujimura–Sugihara equation of motion (Eq. 3):
$$m\,\frac{d^2\vec x}{dt^2} = F\,\vec n - k\,\frac{d\vec x}{dt}$$
m = player mass (kg); F = driving-force magnitude (N); n = unit direction of the force; k = viscous coefficient (kg/s). Dividing by m: $\dot{\vec v} = \alpha\,(V_{max}\vec n - \vec v)$, with $V_{max}=F/k$ (m/s) and $\alpha=k/m$ (1/s). In 1-D along n this is $\dot v = (V_{max}-v)/\tau$, the same as diPrampero2005 Eq. 11.

Solution from x0 = (0, 0), initial velocity v0, constant n (Eq. 4–6):
$$\vec x(t) = \frac{1-e^{-\alpha t}}{\alpha}\,\vec v_0 + V_{max}\left(t - \frac{1-e^{-\alpha t}}{\alpha}\right)\vec n$$
$$A(\alpha,t) = \frac{1-e^{-\alpha t}}{\alpha}, \qquad B(\alpha,V_{max},t) = V_{max}\left(t - A(\alpha,t)\right)$$
Reachable set after t: circle with centre $A\,\vec v_0$ and radius $B$ (m).

Circle estimate from heat maps (Eq. 7–8):
$$(x_c,y_c)=\left(\frac{x_{max}+x_{min}}{2},\frac{y_{max}+y_{min}}{2}\right), \qquad r_c=\frac{x_{max}-x_{min}+y_{max}-y_{min}}{4}$$
Then α from $x_c = A(\alpha,\Delta t)\,v_0$ (regression slope over v0 ≤ 6 m/s) and V_max from $r_c = B(\alpha,V_{max},\Delta t)$.

Proposed extension (Eq. 9), not fitted:
$$m\,\frac{d^2\vec x}{dt^2} = F(t)\,\vec n - k(t)\,\frac{d\vec x}{dt}$$

## Limitations
- One pooled parameter set for all outfield players and all situations; it describes the outer edge of what anyone did (an envelope), not a typical player. No per-player or per-position values, no distributions.
- Parameters depend on Δt, which contradicts the model's constant-parameter assumption (p. 6). The short-Δt values (V_max 14.5 m/s at 1 s) are not realistic top speeds (elite top speeds are ≈ 9–10 m/s); start accelerations α·V_max of 10–18 m/s² at Δt = 1–2 s are far above measured sprint starts (6.4 m/s² in diPrampero2005).
- Extremes (max/min of the heat map) are sensitive to the ±1 m tracking error and to outliers; the large-v0 bins (> 6 m/s) have few points and are unreliable (p. 6).
- The model is isotropic: the same force in every direction. At high speed it allows very hard reversals (deceleration α(V_max + v)), which the data at v0 > 6 m/s cannot confirm.
- Velocity from 1-s differences smooths acceleration onsets.
- Only sprint-like (boundary) behaviour is modelled; no energy, fatigue or reaction time.

## Use in Running Battery
- Simulator: use the vector form $\dot{\vec v} = (V_{max}\vec n - \vec v)/\tau$ for player movement toward the target, with per-player parameters drawn from sensible ranges, not the paper's pooled short-Δt values. Suggested defaults (synthesis of this paper's long-Δt values, diPrampero2005 and Bangsbo2006; my recommendation, flag as such):
  - τ = 1/α: default ≈ 1.1 s, range ≈ 0.9–1.4 s (Narizuka Δt = 2–5 s: 0.96–1.2 s; di Prampero subject 7: 1.42 s; Fujimura–Sugihara: 0.77 s).
  - V_max: default ≈ 8.5 m/s (30.6 km/h), range ≈ 7.5–9.5 m/s (27–34 km/h) (Bangsbo2006 match peak ≈ 8.9 m/s; Narizuka long-Δt ≈ 9.4–10 m/s envelope; sprinters 9.5–10 m/s).
  - Implied start acceleration V_max/τ ≈ 6–9 m/s²; consider a cap near 6–7 m/s² and a separate cap on braking (our idea, not from the paper), because the isotropic model gives unrealistically hard reversals at speed.
  - Fatigue hook: lower V_max (and possibly raise τ) as the hidden fatigue grows; this changes the arrival circle radius B directly, which feeds pitch control.
- Fatigue estimator: the estimator can fit per-player V_max and τ online from observed sprint bouts (straight-line segments are common up to ~10 s, Fig. 2) and track a drop in V_max as a fatigue signal.
- Agents / claims: allowed: "a simple force-plus-drag model reproduces the circular reachable area seen in J1 League tracking data"; not allowed: claims that players can reach 11–14 m/s, or per-player parameters from this paper.
- Overlay / UI: arrival circle (centre A·v0, radius B) is a clear visual for "how far can he get in 1 s / 2 s"; a tired player's smaller circle shows the effect of fatigue on play.

## Ideas or questions it raised
- READING_LIST check: listed as "preprint, arXiv:2205.04511" and "realistic sprint/motion model fitted on tracking data". Imprecise: (1) the file is the peer-reviewed Scientific Reports 13:865 (2023) version; (2) it does not propose a new model, it validates the existing Fujimura–Sugihara (2005) model; (3) parameters are one pooled envelope (not per player) and vary with Δt; the 1–2 s values (V_max 11–14.5 m/s) are not usable as realistic defaults.
- The model is the same first-order law as diPrampero2005's speed curve, which lets us use one motion law in both the simulator and the metabolic-power derivation (closed-form P_met for a simulated sprint).
- Our synthetic data has no tracking error, so if we redo this heat-map analysis on our own output we should get Δt-independent α and V_max. A nice sanity check that the simulator behaves like the model, and an easy demo figure.
- Elliptical vs circular debate (Brefeld 2019, Fernández & Bornn 2018 vs Anzer 2022 and this paper): with narrow v0 bins the circle holds for v0 ≤ 6 m/s; above that the data are too sparse to decide.

Conversion quality: partial — prose is good, but all display equations (Eq. 1–9) are missing from the .md, Greek letters are garbled ("Delta1 t"), and figures are absent. Use the PDF for equations and Fig. 7 values.
