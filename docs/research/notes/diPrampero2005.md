# diPrampero2005: Sprint running as uphill running (equivalent slope, equivalent mass)
Citation: di Prampero PE, Fusi S, Sepulcri L, Morin JB, Belli A, Antonutto G (2005). Sprint running: a new energetic approach. J Exp Biol 208(14):2809–2816. DOI: 10.1242/jeb.01700
Type: lab study (theory + small field measurement)
Context: not football. 12 medium-level male sprinters (age 21.0 ± 2.7 yr, mass 74.2 ± 7.0 kg, stature 1.80 ± 0.06 m, 100 m best 11.30 ± 0.35 s), one all-out run each from starting blocks on an outdoor tartan track; speed measured by radar (Stalker ATS) at 35 Hz, filtered with a 4th-order zero-lag Butterworth; only the first 30 m analysed. Plus one worked example from published split data of C. Lewis (Seoul 1988, 9.92 s).
Evidence strength: low–medium as data (n = 12, one trial each, no direct energy measurement), but high as the theoretical basis that Osgnach2010 and all GPS "metabolic power" systems rely on.

## Definitions and thresholds
- Forward acceleration a_f; resultant acceleration g' = vector sum of a_f and g.
- Equivalent slope (ES): the uphill slope at constant speed that puts the body at the same angle to the ground as during the acceleration.
- Equivalent normalised body mass (EM) = g'/g: the overload from the acceleration.
- Energy cost C (J/kg/m): energy per kg per metre, above resting.
- Metabolic power P_met = C × speed (W/kg), above resting.
- Speed model: mono-exponential rise to maximal speed with time constant τ (Eq. 10).
- No speed or power thresholds are defined.

## Key numbers   (each with page/table/figure)
Pages are journal pages (2809–2816 = PDF pages 1–8).

Group results (n = 12):

| Variable | Mean ± SD | Source |
|---|---|---|
| Peak speed | 9.46 ± 0.19 m/s (34.1 km/h), reached after ≈ 5 s | p. 2812; Table 2 |
| Peak forward acceleration | 6.42 ± 0.61 m/s², at ≈ 0.2 s after the start | p. 2812; Table 2 |
| Peak ES | 0.64 ± 0.06 (abstract: 0.643 ± 0.059); "about 0.70" in the discussion | Table 2; p. 2813 |
| Peak EM | 1.20 ± 0.03 | Table 2 |
| CV peak speed / peak acceleration | 0.020 / 0.095 | Table 2 |
| Mean C over first 30 m | 10.7 ± 0.59 J/kg/m | Table 3 |
| Peak C | 43.8 ± 10.4 J/kg/m | Table 3 |
| Mean P_met over first 4 s | 61.0 ± 4.66 W/kg | Table 3 |
| Peak P_met | 91.9 ± 20.5 W/kg | Table 3 |
| C at constant speed on flat | 3.6 J/kg/m (Minetti) in Methods; "about 3.8" in Results and Discussion | p. 2812; p. 2815 |

Example subject 7 (Figs 2–7, pp. 2811–2813):

| Variable | Value | Source |
|---|---|---|
| Speed curve | s(t) = 10.0 (1 − e^(−t/1.42)) m/s, so s_max = 10.0 m/s, τ = 1.42 s | Fig. 2 caption |
| Fit quality | modelled vs measured speed: y = 0.99x + 0.08, r² = 0.99 (N = 234); all subjects r² > 0.98 | Fig. 3; p. 2813 |
| Peak C | ≈ 50 J/kg/m right after the start | p. 2812; Fig. 6 |
| Mean C over 30 m | ≈ 11.4 J/kg/m (≈ 3× constant-speed running) | Fig. 6 |
| Peak P_met | ≈ 100 W/kg after ≈ 0.5 s | p. 2813; Fig. 7 |
| Mean P_met over 4 s | ≈ 65 W/kg | Fig. 7 |
| ES and EM after ≈ 30 m | ES → 0, EM → 1 (constant speed) | Fig. 5 |
| Main driver of extra cost | ES (EM plays a "marginal role") | p. 2812; Fig. 6 |

C. Lewis 100 m (p. 2814): peak ES 0.80, peak EM 1.3, peak C 55 J/kg/m, peak P_met 145 W/kg; total energy over 100 m 650 J/kg; anaerobic share ≈ 560–600 J/kg (τ_VO2 10–23 s), i.e. ~580 J/kg; maximum anaerobic store estimate 1250 (lactate) + 430 (PCr) = 1680 J/kg.

Air resistance and downhill (pp. 2814–2815):
- k' ≈ 0.40 J·s²·m⁻³ per m² of body surface area; C_aer ≈ 0.86 J/kg/m at the highest speeds; at 9.46 m/s ≈ 20% of total cost and ≈ +8 W/kg.
- Downhill (deceleration): from 0 to −0.45 the cost changes by a factor of ~2 only, minimum 1.75 J/kg/m at slope −0.20, back to ≈ 3.8 J/kg/m at −0.45. Uphill: ≈ 5-fold increase from level to +0.45.
- Typical elite sprinter VO2max ≈ 25 W/kg (≈ 70 mL O2/kg/min) above resting (p. 2814); 1 mL O2 = 20.9 J (p. 2814).

## Equations     (LaTeX, with variable definitions and units; mark "checked against PDF")
All checked against PDF (pp. 2810–2812, 2814–2815).

Resultant acceleration and lean angle (Eq. 1–2):
$$g' = \sqrt{a_f^2 + g^2}, \qquad \alpha = \arctan\frac{g}{a_f}$$
a_f = forward acceleration (m/s²); g = 9.81 m/s²; α = angle between body (COM–foot line) and terrain.

Terrain angle and equivalent slope (Eq. 3–4):
$$\alpha' = 90^\circ - \alpha = 90^\circ - \arctan\frac{g}{a_f}, \qquad ES = \tan\!\left(90^\circ - \arctan\frac{g}{a_f}\right)$$
Note (my simplification, exact): ES = a_f / g.

Forces and equivalent mass (Eq. 5–8):
$$F' = M_b g',\quad F = M_b g,\quad \frac{F'}{F} = \frac{g'}{g}, \qquad EM = \frac{g'}{g} = \sqrt{\frac{a_f^2}{g^2} + 1}$$
M_b = body mass (kg); F' = average muscle force over the stride (N). Equivalent extra mass ΔM = M_b (g'/g − 1).

Speed model and its derivatives (Eq. 10–12):
$$s(t) = s_{max}\left(1 - e^{-t/\tau}\right),\qquad a_f(t) = \frac{ds}{dt} = \frac{s_{max} - s(t)}{\tau},\qquad d(t) = s_{max}\,t - s_{max}\left(1 - e^{-t/\tau}\right)\tau$$
s = speed (m/s); s_max = maximal speed (m/s); τ = time constant (s); d = distance (m). The paper prints a_f as [s_max − s_max(1 − e^{−t/τ})]/τ, which equals (s_max − s)/τ. This is the same first-order law as the Fujimura–Sugihara model in Narizuka2023 (α = 1/τ, V_max = s_max).

Minetti 2002 uphill cost, valid for slopes −0.45 to +0.45 (Eq. 13):
$$C = 155.4x^5 - 30.4x^4 - 43.3x^3 + 46.3x^2 + 19.5x + 3.6$$
x = incline (tangent of α'); C in J/kg/m.

Energy cost of sprint running (Eq. 14):
$$C_{sr} = \left(155.4ES^5 - 30.4ES^4 - 43.3ES^3 + 46.3ES^2 + 19.5ES + 3.6\right)EM$$

With air resistance, final formula (Eq. 19–20):
$$C_{sr} = \left(155.4ES^5 - 30.4ES^4 - 43.3ES^3 + 46.3ES^2 + 19.5ES + 3.6\right)EM + k' v^2$$
$$P_{met} = C_{sr}\cdot s = \left(\ldots\right)EM\cdot s + k' v^2 s$$
v = air speed (m/s; v = s in calm air); s = ground speed (m/s). k' is given as ≈ 0.40 J·s²·m⁻³ per m² body surface area; to use it per kg one must multiply by body surface area and divide by mass. My calculation: for BSA ≈ 1.9 m² and 74 kg, k' ≈ 0.010 J·s²·kg⁻¹·m⁻³, giving ≈ 0.9 J/kg/m at 9.46 m/s, consistent with the paper's 0.86.

Energy balance used for the Lewis example (Eq. 15):
$$E_{tot} = A_{ns} + \dot V_{O_2max}\,t_e - \dot V_{O_2max}\left(1 - e^{-t_e/\tau}\right)\tau$$
E_tot = total energy (J/kg); A_ns = anaerobic energy (J/kg); t_e = performance time (s); τ = VO2 time constant (10–23 s).

## Limitations
- Not football: 12 sprinters, straight-line maximal sprint from blocks, one trial each, first 30 m only.
- No direct energy measurement; C and P_met are indirect estimates "in O2 equivalents" of ATP use, and the authors say direct validation is hardly possible (p. 2814).
- Assumptions (pp. 2810, 2813): mass at the centre of mass (limb work ignored → values are minimal); force only in the sagittal plane; landing phase same as in uphill running; ES and EM are "in excess" of normal constant-speed running lean; uphill cost data (steady-state, aerobic) applied to largely anaerobic sprinting; slopes > 0.45 extrapolated (affects only the first ~3 m).
- Acceleration is obtained from the fitted exponential, not from raw data. This smooths step-to-step swings. Buchheit2015 argues that soccer accelerations are shorter and not mono-exponential, so the model may not transfer.
- Minor inconsistencies: flat cost 3.6 vs 3.8 J/kg/m; unit typo "3.6 J/kg/min" (p. 2812); peak ES 0.64 (Table 2) vs "about 0.70" (p. 2813).

## Use in Running Battery
- Simulator: the speed law s(t) = s_max(1 − e^(−t/τ)) and a_f = (s_max − s)/τ is a good straight-line sprint model and matches Narizuka2023's model. Sprinter reference values: s_max ≈ 9.5–10 m/s, τ ≈ 1.4 s, initial acceleration s_max/τ ≈ 6–7 m/s² (Table 2: 6.42 m/s²). Football players should be set a bit lower in top speed (see Bangsbo2006: peak ≈ 8.9 m/s).
- Fatigue estimator: gives the derivation behind Osgnach2010. Adds two things Osgnach does not use: (1) the air-resistance term k'v² (≈ +8 W/kg at 9.5 m/s; at football top speeds ≈ 8–9 m/s it is smaller but not zero); (2) a clear statement that the downhill (deceleration) part of the polynomial is valid down to ES = −0.45 (a ≈ −4.4 m/s²).
- Agents / claims: allowed: "the first steps of a sprint can cost 10× more energy per metre than steady running" (peak C ≈ 44 vs 3.6–3.8 J/kg/m, sprinters). Must say it is from track sprinters, not footballers.
- Overlay / UI: the "uphill" picture (Fig. 1) is a nice explainer for fans: "accelerating = running up a hill whose slope equals acceleration ÷ g".

## Ideas or questions it raised
- READING_LIST check: "physics behind Osgnach2010" is correct. What it adds over Osgnach: the explicit formulas ES = tan(90° − arctan(g/a_f)) and EM = sqrt(a_f²/g² + 1), the air-resistance term (Eq. 19–20), the downhill reasoning, and the mono-exponential speed model.
- Since ES = a_f/g exactly, we can skip the trigonometry in the implementation.
- The same exponential model links motion and energy: a simulated sprint with known s_max and τ gives a closed-form P_met(t), useful as a unit test for the estimator.
- Whether to include k'v² in our estimator: Osgnach left it out (error ≈ 10% at 21 km/h, < 2 min/match above that). For consistency with published Osgnach values, leave it out by default, maybe as an option.

Conversion quality: partial — prose and Tables 1–3 are fine, but all display equations (Eq. 1–20) are missing from the .md, including the final formula (Eq. 19–20). Use the PDF for equations.
