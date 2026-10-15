# daSilva2025: Pitch control with player-specific top speed and a "stamina factor"
Citation: da Silva MF, Novillo Á, Aleta A, López del Campo R, Resta R, Moreno Y, Buldú JM (2025). The interplay between pitch control and top speed in soccer considering the stamina factor. Scientific Reports 15:38799. doi:10.1038/s41598-025-22778-6. (READING_LIST also gives arXiv:2504.18250; not checked here.) Article licence: CC BY-NC-ND 4.0 (PDF p. 12), so we must not copy its figures into our repo. Code: github.com/Markfds01/Tracking_laliga (MIT licence, per the repo README).
Type: method (modelling / simulation study on match tracking data)
Context: LaLiga 1st division, elite men, season 2019/20 (all matches before the COVID-19 break), 100 matches, all 20 teams (Fig. 4 says each team is averaged over 10 matches). Tracab optical tracking (multi-camera), 25 Hz, spatial resolution "up to 10 cm" (PDF pp. 2–3). Substitutes excluded. Goalkeepers left out of the player-level results.
Evidence strength: medium for the method, low for any fatigue claim. The data are a large real dataset, but the "stamina factor" is a **made-up multiplier on top speed for what-if runs, not a measured fatigue state**. Every stamina result is the output of the model, not something observed on the pitch. The ΔPC values in Figs. 6–8 have **no stated units or normalisation**, so we can only use them for direction and shape, not size.

## Definitions and thresholds
| Term | Definition | Source |
|---|---|---|
| Pitch control (PC) at a location | Probability that a player/team gains possession if the ball is sent straight there | PDF p. 3 |
| Classical PC | Every player gets the same top speed v_max,p = 5 m/s (18 km/h) | PDF p. 3 |
| v95(i) | 95th percentile of player i's speed distribution, computed **per half** of each match. Used as that player's "top speed" | PDF p. 4 |
| PC_v | Speed-dependent pitch control: v_max,p replaced by v95(i) | PDF p. 4 |
| Stamina factor ξ | Multiplier on top speed: v_max,p(i) = ξ · v95(i). ξ>1 faster, ξ<1 slower. Tested from 0.8 to 1.5 in steps of 0.1 (Figs. 6a, 7, 8). Applied to a whole team (Figs. 6, 7) or to all players of one role in a team (Fig. 8) | PDF pp. 4, 7–9 |
| ΔPC_v | Change in accumulated PC_v when ξ ≠ 1, compared with ξ = 1. Units and normalisation **not defined** in the paper | PDF p. 7, Fig. 6a |
| λ_s | Slope of the fit ΔPC_v = λ_s log ξ + b, fitted per team per match, then averaged per team ⟨λ_s⟩ | PDF p. 7 |
| PC_v^90 | Pitch control a player accumulates over 90 effective minutes, "normalized" (method of normalisation not given) | Fig. 3 |
| Attack/defence | Frames split by which team has the ball (possession flag in the data) | PDF pp. 3, 8 |

v95 is **not** a sprint peak. It is about 5 m/s (18 km/h), well below match peak sprint speeds (around 8–9 m/s in other papers). The authors pick it as "the top speed achievable when contesting for ball control". In the code the goalkeeper's top speed is the 99th percentile instead (velocities.py, `GK_percentile=99`; not mentioned in the paper).

## Key numbers   (each with page/table/figure)
Model parameters (PDF p. 3 unless stated):
| Parameter | Value | Note |
|---|---|---|
| Ball speed v_b | 15 m/s (54 km/h), constant, straight line | p. 3 |
| Default top speed v_max,p | 5 m/s (18 km/h) | p. 3 |
| Reaction time t_r | 0.7 s (player keeps current velocity during it) | p. 3, cites ref 28 = Laurie Shaw's "LaurieOnTracking" code, not Spearman |
| Control rate λ | 4.3 s⁻¹ | p. 3, from Spearman2017 |
| Goalkeeper control rate λ_GK | 12.9 s⁻¹ (= 3 × 4.3) | p. 3 |
| Arrival-time uncertainty σ | **value not given in the paper**. Code: `tti_sigma = 0.45` s | p. 3; pitch_control.py |
| Integration window | t ∈ [t_ball, t_ball + 10] s in the paper. Code: `max_int_time = 50` s with early stop at tolerance 0.01 | p. 4; pitch_control.py |
| Integration step | not given in the paper. Code: `int_dt = 0.04` s | pitch_control.py |
| Grid | not given in the paper. Code: 50 cells along a 106 × 68 m pitch (50 × 32 cells, about 2.1 m) | pitch_control.py |
| Acceleration | **not used** in the time-to-intercept (the code has `max_player_accel = 7` but never uses it) | p. 3, Eq. 1; player.py |
| Defender control-rate scaling κ | not used (code `kappa_def = 1`) | pitch_control.py |
| Velocity smoothing | not given in the paper. Code: moving average over 7 frames, raw speeds > 12 m/s set to missing | velocities.py |
| Compute cost / frames used | not reported. The code takes a frame step argument; the value used is not stated | main.py |

v95 by position (approx., read from Fig. 1, PDF p. 4; LaLiga 2019/20, Tracab 25 Hz, per half):
| Position | Median v95 | IQR | Whiskers |
|---|---|---|---|
| Defenders | ≈ 5.08 m/s (18.3 km/h) | ≈ 4.85–5.38 m/s | ≈ 4.2–6.1 m/s |
| Midfielders | ≈ 5.32 m/s (19.2 km/h) | ≈ 5.10–5.53 m/s | ≈ 4.45–5.95 m/s (outliers to 6.2) |
| Forwards | ≈ 5.38 m/s (19.4 km/h) | ≈ 5.18–5.57 m/s | ≈ 4.65–6.1 m/s (outliers 4.1, 4.45, 6.15) |

Player PC_v^90 against v95 (approx., read from Fig. 3, PDF p. 6):
| Position | Pearson r | PC_v^90 range | Slope of fitted line (approx.) |
|---|---|---|---|
| Defenders | 0.72 | ≈ 0.04–0.16 | ≈ 0.06 per m/s |
| Midfielders | 0.62 | ≈ 0.02–0.10 | ≈ 0.04 per m/s |
| Forwards | 0.53 | ≈ 0.03–0.07 | ≈ 0.02 per m/s |
Defenders gather the most pitch control even though they are the slowest (p. 5).

Team level:
- Team PC vs PC_v (Fig. 4, p. 6): teams lie between ≈0.455 and ≈0.54. Barcelona is highest on both. Above the identity line (gain when real speeds are used): Sevilla, Osasuna, Atlético (p. 9). Below: Real Valladolid, Villarreal (p. 9).
- Halves (Fig. 5, p. 7): team ⟨ΔPC_v⟩ per half ranges about −0.05 to +0.05 around the league mean. Atlético is average in the 1st half and "decays drastically" in the 2nd (≈ 0 → ≈ −0.02, approx. from Fig. 5). Getafe gains more PC in the 2nd half than Real Madrid (p. 7). Because v95 is computed per half, this half-split includes real speed differences between halves, but the paper does not report how v95 changes from the 1st to the 2nd half.

Stamina factor (all model outputs):
| Result | Value | Source |
|---|---|---|
| Fit form | ΔPC_v = λ_s log ξ + b | p. 7 |
| Log base | not stated. Natural log fits the figure: Real Valladolid ⟨λ_s⟩ ≈ 1.35 gives 1.35·ln 1.5 ≈ 0.55 and 1.35·ln 0.8 ≈ −0.30, matching Fig. 6a (≈ 0.58 and ≈ −0.29) | our check on Fig. 6 |
| ⟨λ_s⟩ across teams | ≈ 0.98 (Barcelona) to ≈ 1.35 (Real Valladolid); league mean ≈ 1.14 (dashed line) | approx., read from Fig. 6b, p. 8 |
| Most sensitive teams | Real Valladolid, Alavés, Valencia | Fig. 6b, p. 9 |
| Least sensitive teams | Barcelona, Sevilla, Espanyol | Fig. 6b, p. 9 |
| ΔPC_v for one match, ξ = 0.8 | ≈ −0.15 (Barcelona) to ≈ −0.29 (Valladolid) | approx., Fig. 6a |
| ΔPC_v for one match, ξ = 0.9 | ≈ −0.07 to ≈ −0.14 | approx., Fig. 6a |
| ΔPC_v for one match, ξ = 1.5 | ≈ +0.27 to ≈ +0.58 | approx., Fig. 6a |

Attack vs defence, ΔPC_v^att − ΔPC_v^def (approx., read from Fig. 7, p. 8; points = team means, bars = 1 SD):
| ξ | 0.8 | 0.9 | 1.0 | 1.1 | 1.2 | 1.3 | 1.4 | 1.5 |
|---|---|---|---|---|---|---|---|---|
| att − def | +0.03 | +0.02 | 0 | −0.03 | −0.06 | −0.10 | −0.13 | −0.17 |
Meaning: speed changes matter more when **defending**. A slower team (ξ < 1) loses more pitch control when defending than when attacking (p. 8).

By role, ⟨ΔPC_v⟩ per modified player (approx., read from Fig. 8, p. 9; only that role's top speed changed):
| ξ | Defenders | Midfielders | Forwards |
|---|---|---|---|
| 0.8 | −0.025 | −0.013 | −0.027 |
| 0.9 | −0.012 | −0.007 | −0.016 |
| 1.1 | +0.011 | +0.011 | +0.022 |
| 1.2 | +0.020 | +0.023 | +0.048 |
| 1.3 | +0.027 | +0.037 | +0.077 |
| 1.4 | +0.033 | +0.052 | +0.106 |
| 1.5 | +0.040 | +0.068 | +0.134 |
For **speed gains**, forwards gain most and defenders least. For **speed losses** (the fatigue case, ξ < 1) the effects are small and similar for defenders and forwards. Midfielders lose least (p. 9: "a decrease produces much more moderate differences").

Space in m² per % of top speed lost: **not reported**. The paper gives PC as a share, not as area, and does not define the units of ΔPC_v. A conversion to m² would be our own guess.

## Equations     (LaTeX, with variable definitions and units; checked against PDF, pp. 3–4)
Ball arrival time (unnumbered, p. 3):
$$\tau_{\text{ball}} = \frac{\Delta x_b}{v_b}$$
Δx_b = distance from ball to target [m]; v_b = 15 m/s.

Player arrival time, Eq. (1):
$$\tau_{\text{player}}(\vec r, t_r) = t_r + \frac{|\vec r - \vec r_{\text{react}}|}{v_{\max,p}}$$
t_r = 0.7 s reaction time; $\vec r_{\text{react}}$ = position after moving for t_r at current velocity [m]; v_max,p = top speed [m/s] (5 m/s classical, v95(i) speed-dependent, ξ·v95(i) with stamina). No acceleration phase.

Interception probability, Eq. (2) (logistic CDF):
$$F_{\text{int},j}(\vec r, t, \sigma, t_r) = \frac{1}{1 + e^{-\frac{t - \tau_j(\vec r, t_r)}{\sqrt{3}\,\sigma/\pi}}}$$
t = time [s]; τ_j = arrival time of player j [s]; σ = arrival-time uncertainty [s] (value not given; code 0.45 s).

Control probability, Eq. (3):
$$\frac{dPC_j}{dt}(t, \vec r, \sigma, \lambda_j, t_r) = \Big(1 - \sum_k PC_k(t, \vec r, \sigma, \lambda_k)\Big)\, F_{\text{int},j}(t, \vec r, \sigma, t_r)\, \lambda_j$$
λ_j = control rate [s⁻¹] (4.3; GK 12.9). Integrated over t ∈ [t_ball, t_ball + 10] s from PC_j = 0. The team PC is the sum over teammates. (The sum runs over all players including j, as in the code.)

Stamina factor (p. 4):
$$v_{\max,p}(i) = \xi \cdot v_{95}(i)$$

Logarithmic fit (p. 7):
$$\Delta PC_v(\xi) = \lambda_s \log \xi + b$$
λ_s = team sensitivity (same units as ΔPC_v, undefined); b = offset (≈ 0 since ΔPC_v(1) = 0). Base of the log not stated (natural log fits the figures).

## Limitations
- **The stamina factor is assumed, not measured.** ξ is a what-if knob, applied evenly to a whole team or role group, held fixed for the whole match. It is never estimated from fatigue, running load or time in the match.
- The authors call players who run slower "conserving energy" and faster ones "over-motivated" (p. 4). They do not separate fatigue, tactics or pacing.
- ΔPC_v units and normalisation are not defined (Figs. 6–8). Values like 0.58 at ξ = 1.5 cannot be a change in a team share that starts near 0.5 (it would exceed 1), so they must be summed, relative or percentage values. We cannot tell which. Use only the shape and ranking.
- No acceleration in the movement model, and v95 (≈5 m/s) is not a capacity measure. Fatigue that cuts acceleration more than top speed cannot be expressed in this model.
- σ, grid, time step and frame sampling are missing from the paper (taken from the code above). The paper's 10 s window differs from the code's 50 s (with early stop).
- One league, one season, no tactical data (pp. 9–10). Pearson r values in Fig. 3 are low to moderate. Other factors matter.
- No significance tests or CIs, except SD bars in Figs. 7–8.
- No validation of PC against real outcomes (for example, who actually won the ball).

## Use in Second Wind
- Simulator: no direct parameters for movement. If the simulator wants to "feel" fatigue in space control, the same model can be run on synthetic frames with each player's hidden effective top speed. Typical v95 values (≈5.1/5.3/5.4 m/s for D/M/F, Fig. 1) are a realism target for the 95th percentile of the synthetic speed distribution per half.
- Fatigue estimator: gives the bridge "fatigue → lower effective top speed → less pitch control". Set ξ_i(t) = v_eff,i(t) / v95_i,fresh, where v_eff comes from our estimator (battery/peak-spell state). **The size of the speed drop must come from other papers** (sprint/peak-speed decline studies), not from this one.
- Agents / claims: supported: "in a pitch-control model, a slower player controls less space, and the loss is larger when defending" (model result, Figs. 7–8). "Slowing a whole team by 10% cuts its pitch control in a roughly logarithmic way" (Fig. 6, model). Not supported: any number in m², any claim that LaLiga players were measured to lose space because of fatigue, any claim that forwards lose most when tired (that is true only for speed gains).
- Overlay / UI: a "space lost to fatigue" layer: PC map with fresh v95 vs PC map with ξ·v95, and the difference shaded. Label as "model estimate".

## Ideas or questions it raised
- READING_LIST says the paper "links stamina to the space a player controls" and "how the stamina factor lowers top speed". Imprecise: stamina is not measured. ξ is a fixed hypothetical multiplier on v95, the same for a whole team or role, between 0.8 and 1.5. The "logarithmic effect" is real but has no usable units. The title in READING_LIST is slightly off (real title: "The interplay between pitch control and top speed in soccer considering the stamina factor").
- PLAN.md's "Low energy lowers top speed and acceleration [... daSilva2025]": this paper only shows the effect of lower top speed on pitch control, in a model with no acceleration. It does not show that low energy lowers top speed.
- Our synthetic data has the true fatigue, so we can do what this paper could not: compute the per-player, time-varying ξ and check whether PC loss tracks true fatigue.
- Their parameter set (0.7 s reaction, 5 m/s, σ 0.45 s, λ 4.3, λ_GK 12.9, ball 15 m/s) is the Laurie Shaw / Friends-of-Tracking version of Spearman. Using the same defaults makes our numbers comparable with theirs.
- Open question: what ξ range is realistic for in-match fatigue? A 0.8 factor (−20%) is probably far larger than real fatigue-related drops in v95. Other readers' papers on peak-speed decline should set this.

Conversion quality: partial. Text is good. Equations 1–3 are placeholders or garbled in the .md (checked against PDF images). All figures (the only source of the stamina numbers) are missing, so values were read from the PDF figures.
