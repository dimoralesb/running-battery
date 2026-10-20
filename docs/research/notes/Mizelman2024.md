# Mizelman2024: Critical speed models fitted to GPS speed-duration profiles
Citation: Mizelman E, Pearson A, Chu D, Clarke DC (2024). Critical speed models of high-resolution speed-duration profiles describe peak running demands in soccer. International Journal of Sports Science & Coaching 19(5):2056–2066. doi:10.1177/17479541241246951
Type: method (observational field study, model comparison)
Context: Seattle University, NCAA Division I men (US collegiate, not professional). 15 players (3 forwards, 7 midfielders, 4 defenders, 1 midfield/defence). August–September 2019, 6 weeks, 42 sessions (7 matches, 35 practices); players took part in 33 ± 6.1 sessions (range 16–38): 27 ± 4.8 practices, 5 ± 1.6 games (p. 2058). GPS: SPT2 (Australia), 10 Hz, worn between the scapulae. Validity vs radar: RMSD 0.84 m/s, CV 11.8%; inter-unit RMSD 0.70 m/s, CV 9.0% (p. 2058).
Evidence strength: medium-low for our use. It is a careful method paper with open code, but: small sample (n = 15), collegiate level, practices and games pooled, and the authors themselves say the fitted "CS" (~2 m/s) is far below real physiological CS and should NOT be read as CS (p. 2064).

## Definitions and thresholds
- Speed-duration profile: for each duration d from 0.1 s to 600 s (0.1 s steps, ~6000 durations), the maximum of the moving average of speed over any window of length d. Built per session ("session-specific") and over all 6 weeks ("global") (p. 2058).
- Cleaning: removed NA values, low-quality GPS (HDOP > 2) and speeds above ~12 m/s (43 km/h) (p. 2058).
- Profiles were truncated to 2–600 s for fitting, because all models departed from the data below ~1 s (p. 2059). Below 1 s the profile was flat in some players because of the 12 m/s filter (p. 2064).
- Fit: nonlinear least squares (R `minpack.lm::nlsLM`, Levenberg–Marquardt), parameters bounded. Goodness of fit: RMSE (SD of residuals), AIC, BIC; compared with linear mixed models (model = fixed, player = random) and Tukey post hoc (p. 2059).
- Code: R package `critspeed`, https://github.com/aaronzpearson/critspeed (p. 2059). R and Python implementations gave identical results (p. 2059).

## Key numbers   (each with page/table/figure)
Peak (maximal mean) speeds, global profiles, n = 15 (Table 2, p. 2060):

| Duration | Mean m/s (m/min) | SD m/s (m/min) | 95% CI m/s |
|---|---|---|---|
| 60 s | 3.60 (216) | 0.38 (23) | 3.54–3.65 |
| 180 s | 2.56 (154) | 0.32 (19) | 2.51–2.61 |
| 300 s | 2.32 (139) | 0.33 (20) | 2.28–2.37 |
| 600 s | 2.17 (130) | 0.27 (16) | 2.13–2.21 |

Model parameters, global 2–600 s profiles, mean ± SD (min, max) (Table 3, p. 2062):

| Model | CS m/s | D′ m | Smax m/s | RMSE | AIC | BIC |
|---|---|---|---|---|---|---|
| CS2 | 2.4 ± 0.3 (2.1, 3.3) [8.6 (7.6, 11.9) km/h] | 26.0 ± 3.4 (18, 33) | n/a | 0.44 ± 0.10 | 6800 ± 3100 | 6800 ± 3100 |
| 5PL | 2.0 ± 0.4 (1.3, 3.2) (lower asymptote c) | n/a | 10.2 ± 1.5 (7.9, 12.0) (upper asymptote d) | 0.09 ± 0.03 | −12,100 ± 4400 | −12,000 ± 4000 |
| CS3 | 2.0 ± 0.4 (1.7, 3.2) [7.2 km/h] | 106 ± 29 (39, 150) | 9.6 ± 1.2 (8.1, 12.0) | 0.11 ± 0.04 | −10,600 ± 4600 | −10,500 ± 4600 |
| OmSD | 2.1 ± 0.4 (1.7, 3.2) | 79 ± 21 (32, 111) | 8.6 ± 1.0 (7.3, 10.7) | 0.12 ± 0.04 | −9100 ± 4000 | −9100 ± 4000 |

5PL shape parameters (Table 3): a = −2.01 ± 2.66 (−0.43, −8.99); b = 5.69 ± 4.90 (0.18, 12.9); f = 50.1 ± 83.9 (0.053, 238).

- Which model fits best: CS2 is clearly worst (all metrics significantly worse). 5PL, CS3, OmSD are not significantly different; order of fit 5PL > CS3 > OmSD (p. 2061, Table 3). The authors prefer CS3/OmSD because their parameters are interpretable and they have fewer parameters than 5PL (p. 2063–2064).
- CS2 CS was significantly higher than the other models; CS from CS3, 5PL, OmSD did not differ (p. 2060). OmSD Smax significantly lower than 5PL (P = 0.0017) (p. 2060). OmSD D′ significantly lower than CS3 (Table 3 footnote c).
- CS2 fitted only on 120–600 s gave "satisfactory" fits (data not shown) (p. 2064).
- Between-player differences are real: likelihood-ratio tests for player random effect, CS χ² = 54, P = 2 × 10⁻¹³; D′ χ² = 12, P = 4 × 10⁻⁴ (p. 2060).
- Session-specific CS3 fits, games vs practices (Fig. 4, p. 2061): CS 1.6 ± 0.5 vs 1.3 ± 0.4 m/s (P = 2 × 10⁻⁶); Smax 7.6 ± 1.7 vs 6.7 ± 1.3 m/s (P = 5 × 10⁻⁹); D′ 52.3 ± 44.2 vs 53.3 ± 41.7 m (P = 0.57, no difference). Note: single-session D′ (~52 m) is about half of the global D′ (106 m) and very noisy (SD ~ 85% of mean).
- Positions: the paper does NOT report CS / D′ by position (only n per position, p. 2058). Per-player values are only in Supplementary Tables S1/S2 (not in our PDF).
- Data volume: ~36 × 10⁶ data points; profile computation < 1 min per player for ~38 sessions on a laptop (p. 2059, 2061).
- Context quoted from other literature: professional male 1-, 3-, 10-min peak relative distances ≈ 200, 150, 120 m/min (p. 2057, citing Rico-González 2022). Lord et al. (refs 25, 26) got CS ≈ 4 m/s with CS2 on match data (p. 2064).

## Equations     (LaTeX, with variable definitions and units; mark "checked against PDF")
Checked against PDF (Table 1, p. 2058, viewed as image).

Variables: $S(t)$ = maximal mean speed over duration $t$ (m/s); $t$ = duration (s); $CS$ = critical (asymptotic) speed (m/s); $D'$ = curvature constant (m); $S_{max}$ = maximal instantaneous speed (m/s).

CS2 (two-parameter hyperbolic):
$$S(t) = \frac{D'}{t} + CS$$

CS3 (three-parameter, Morton 1996):
$$S(t) = \frac{D'}{t + \dfrac{D'}{S_{max} - CS}} + CS$$

OmSD (truncated omni-domain speed-duration model, Puchowicz 2020), valid for $t < 1800$ s:
$$S(t) = \frac{D'}{t}\left[1 - e^{-t\,\frac{S_{max} - CS}{D'}}\right] + CS$$

5PL (five-parameter logistic, empirical; $c$ = lower asymptote m/s, $d$ = upper asymptote m/s, $a$ = decrease rate, $b$ = inflection point in log10(s), $f$ = exponent):
$$S(t) = c + \frac{d - c}{\left\{1 + e^{-a[\log_{10}(t) - b]}\right\}^{f}}$$

Power version for reference (Eq. 1, p. 2057): $P(t) = W'/t + CP$.

Note (our observation, not in paper): CS3 and OmSD both give $S(0) = S_{max}$, unlike CS2 which goes to infinity at $t \to 0$.

## Limitations
- Authors' own: residuals systematic, non-normal, autocorrelated; points from the same GPS segment are not independent, so standard CIs are invalid (p. 2063–2064). "Bumps" in some profiles (longer durations faster than shorter) from intermittent play (Fig. 1d, p. 2064). Models assume an asymptote, but real speed keeps falling with duration (p. 2064).
- Most important for us: soccer intermittency makes the fitted CS (~2 m/s = 7.2 km/h, a jog) "likely well below" real CS (estimated ~14 km/h = 3.9 m/s from VO2 data for this level) (p. 2064). Authors propose renaming CS → "asymptotic speed (AS)" and D′ → "curvature constant (CC)" for intermittent-sport data until physiological meaning is proven (p. 2064).
- Collegiate players, one team, 6 weeks, mostly practices (only 7 games). No positional breakdown. Doppler speed preferred but positional differentiation discussed (p. 2064).
- Smax estimates (8.6–10.2 m/s, max 12 m/s) are above typical player top speeds (~9 m/s); 12 m/s is the filter limit, so some values sit at the bound.

## Use in Running Battery
- Simulator: do NOT use these CS/D′ as the hidden physiological truth. A "true" CS should be closer to lab/3MT values (~3.4–4 m/s; see Sutcliffe2025, Liu2021). Use Table 2 peak speeds (3.60 m/s at 60 s, 2.56 m/s at 180 s, 2.32 at 300 s, 2.17 at 600 s) only as a sanity check for collegiate-level synthetic profiles; professional values are higher (~200/150/120 m/min at 1/3/10 min).
- Fatigue estimator: the method (rolling max-mean speed for every duration, fit CS3 or OmSD on 2–600 s) is a valid way to get each player's speed-duration profile from tracking alone. But the resulting "CS" (~2 m/s) used as a W′bal threshold would make the battery drain almost all the time a player jogs. Options: (a) fit only on longer durations (CS2 on 120–600 s, which the authors say fits well, p. 2064), (b) treat the asymptote as a lower bound and use a prior from 3MT values, (c) validate on synthetic data where we know the true CS. Global profiles need many sessions; one session gives very noisy D′ (52 ± 44 m).
- Agents / claims: may say "CS-model fits summarise peak running demands"; may NOT say "CS and D′ from match data equal physiological CS/D′" (authors explicitly deny this).
- Overlay / UI: a player's speed-duration curve (fresh vs current) is a nice visual; the model curve S(t) is cheap to draw.

## Ideas or questions it raised
- READING_LIST says this paper "estimates critical speed and D′ from match/training GPS data, without a lab test… our default player parameters." This is imprecise and risky: the paper shows it can FIT CS models, but the authors say the parameters are probably NOT physiological CS/D′ (CS ~2 m/s is a jog). "D′ around 79–106 m depending on model" is correct for OmSD/CS3 means (Table 3), but CS2 gives 26 m and single sessions ~52 m.
- Positional defaults cannot come from this paper (no position table).
- Test in our synthetic world: generate players with known CS/D′, run the Mizelman fit on synthetic tracking, and measure the bias. This directly shows judges whether "CS from tracking" works.
- The supplement (per-player S1/S2) and the `critspeed` R package could be reused for code (out of scope for this note).

Conversion quality: partial — text good, but Table 1 equations garbled (fractions lost) and Table 3 rows shifted (5PL a/b/f values merged into CS3 row). Use the PDF.
