# Castellano2024: Predicting a team's running from its opponent's running (LaLiga)
Citation: Castellano J, López-Del Campo R, Hileno R. Tell me how much your opponent team runs and I will tell you how much you should run: a predictive model applied to Spanish high-level football. Biol Sport 2024;41(2):275–283. doi:10.5114/biolsport.2024.132984
Type: match study (league-wide, team level) + regression model
Context: LaLiga 2016/17–2019/20, 1,473 matches, 2,946 team performances (96% of possible). TRACAB via Mediacoach; possession from Opta.
Evidence strength: high for the association (whole league, 4 seasons); medium for transfer to the EPL.

## Definitions and thresholds
- Outcomes: team total distance (TotDisTea, km) and distance > 21 km/h (5.83 m/s).
- Predictors: home/away, match outcome, team level and opponent level (final ranking groups), effective playing time (min), possession (min), opponent's distance.

## Key numbers   (each with page/table/figure)
- **Best TD model R²adj = 0.82** (cross-validated R² 0.823), predictors: location, team level, opponent level, effective playing time, possession, opponent TD (Results; Table 3).
- **Equation 1:** TotDisTea = 7.077 + 0.284·Home + (−0.079·L2 + 0.486·L3 − 0.633·L4) + (0.153·O2 + 0.004·O3 + 0.751·O4) + **0.424·EffPlayTime − 0.271·Possession + 0.712·OppTD** (km, min) (Results).
- Without opponent TD: R²adj 0.64 (Equation 2).
- **> 21 km/h distance could not be predicted** (all models R²adj < 0.38) (Results).
- Team TD mean 78.3 ± 6.3 km; effective playing time range 36.8–68.2 min; possession 12.4–49.4 min (Discussion/Limitations). The 78 km mean is far below TRACAB EPL team totals (~110 km); the paper does not explain; likely a different distance definition (e.g. excludes GK or dead time). **Treat absolute values as not comparable.**
- Home: +0.1–0.5 km; facing a Champions League team: +0.4–1.1 km.

## Equations
Equation 1 as above (from .md text; not checked against PDF image).

## Limitations
- LaLiga, older TRACAB data; unexplained low TD scale.
- Team-level only.

## Use in Running Battery
- Simulator: **team running should depend on the opponent's running, effective playing time and own possession.** Coefficients give sensible signs and rough sizes: +0.42 km per extra effective minute; −0.27 km per extra minute of possession; +0.71 km per km the opponent runs. Use as a sanity check, not as exact targets.
- Fatigue estimator: none.
- Agents / claims: "Teams run more when the ball is in play longer and when they don't have the ball" → supported. High-speed totals are hard to predict from context.
- Overlay / UI: pre-match "expected running" forecast vs live actual is a nice analyst feature.

## Ideas or questions it raised
- Agrees with Allen2026a (home–away r 0.68–0.75) and Allen2026b (possession lowers total running).
