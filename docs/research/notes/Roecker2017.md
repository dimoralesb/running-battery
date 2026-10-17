# Roecker2017: Speed–duration profile of soccer matches (sigmoid on log time)
Citation: Roecker K, Mahler H, Heyde C, Röll M, Gollhofer A (2017). The relationship between movement speed and duration during soccer matches. PLoS One 12(7):e0181781. doi:10.1371/journal.pone.0181781
Type: observational, curve fitting.
Context: 38 players from three amateur teams (German men's 5th and 8th tier, women's 4th tier), 82 game participations of ≥ 30 min (8 games). adidas miCoach 10 Hz GPS + IMU, Kalman-filtered. **Moving medians** (not means) over 21 windows from 0.3 to 2,700 s; the best value per window per game. Half-time and stoppages were left in the data (Methods, Data acquisition).
Evidence strength: **low.** PLOS ONE (use with care); amateur and women's teams; funded by adidas, three authors paid by or consulting for adidas. Crossref checked 2026-10-17.

## Key numbers
- A five-parameter logistic (Richards) on log(duration) fits every profile: RMSE 0.10 m/s, R² 0.999 (Table 3). Hyperbolic and exponential models are biased (Fig. 2).
- **Lower asymptote ("critical speed") 1.73 ± 0.24 m/s** (6.2 km/h); 2.08 ± 0.32 when weighted by acceleration. Upper asymptote 7.62 ± 0.69 m/s; men 7.87 ± 0.55 (Tables 4–5).
- Central midfielders have the highest lower asymptote (1.91), centre-backs the lowest (1.48) (Table 4).
- Lower and upper asymptotes are independent (r² = 0.04, Fig. 4).

## Main message
The best speed a player sustains for a given duration in a match follows an S-curve on log time, with a plateau for very short durations (sprinting limits) and a floor for long ones.

## Limitations and errors
- The authors call the lower asymptote "critical speed" and say most players "reached their metabolic limits" (Discussion), but at 1.7–2.5 m/s it is a walking/jogging average, not CS; they note intermittent running lowers it.
- Medians, and half-time inside the 2,700 s window, both pull the long-window values down.
- Mostly 2–3 games per team.

## Use in Second Wind
- **Estimator (3.2.5 option A, 8.1)**: confirms that a match speed–duration profile does not give a physiological CS. With the same kind of data, the "CS" is 1.7 m/s here, 2.0 m/s with CS3/OmSD [Mizelman2024], 3.6–4.0 m/s with a linear 1/t fit [Lord2020].
- **Analyst mode**: the S-curve is a nicer way to draw a player's match speed–duration profile than a hyperbola, if we ever show one. Not planned.
- **Claims**: block per-player "match critical speed" (claim 29).
