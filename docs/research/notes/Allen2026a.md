# Allen2026a: "Run more, win more?" Running load, match outcome and league position in the Premier League
Citation: Allen T, Taberner M, Zhilkin M, Alexander J, Harper D, Rhodes D. Is it as simple as run more, win more? Influence of running load on match outcome and final league position across nine consecutive English Premier League football seasons. Int J Sports Sci Coach 2026;21(3):1504–1512 (online 2025). doi:10.1177/17479541251371004
Type: match study (league-wide, team level)
Context: EPL 2015/16–2023/24, 33 teams, 1,764 players, 3,379 games; 41 untracked and 397 not 11 v 11 removed → **2,982 games**. Optical 25 Hz: TRACAB (2015/16–2018/19), then Second Spectrum, TRACAB converted with Allen2025 equations. Team totals include substitutes (Methods).
Evidence strength: high for the associations (whole league, 9 seasons); correlational only.

## Definitions and thresholds
- TD; HID > 5.5 m/s (incl. sprint); HSR 5.5–7 m/s; SprD > 7 m/s; dwell 0.5 s (HID) / 1 s (SprD).
- League position: teams ranked by each running metric per season, Spearman rs vs final position.
- Win/draw/loss: per-season z-scores, one-way ANOVA, Cohen's d.

## Key numbers   (each with page/table/figure)
- **Final league position vs running (Abstract; Fig. 1):** TD rs = .13 (ns, p = .09); HID rs = .28; HSR rs = .20; **SprD rs = .32**.
- **Home vs away team running in the same match: r = 0.68–0.75** for TD, HID, HSR, SprD (Abstract; Fig. 2).
- Win vs draw / win vs loss effect sizes (Table 2): TD −0.14 / −0.18; HID −0.14 / −0.10; HSR −0.10 / −0.03 (ns); SprD −0.20 / −0.23 (negative = winners higher). Draw vs loss: no differences.
- **Winners vs losers in the same match (Table 3):** TD 113,895 ± 4,378 vs 113,115 ± 4,515 m (+780 m, ES 0.22); HID 8,478 vs 8,368 (+110 m, ES 0.12); HSR +19 m (ns); **SprD 1,935 vs 1,844 (+91 m, ES 0.29)**. Table 3 lists ES 0.22 for HSR despite p = 0.226 (likely a typo).
- Match length 2015/16 96.3 ± 1.7 → 2023/24 101.0 ± 2.9 min (Table 1).

## Equations
None.

## Limitations
- Associations, no causation; no possession, game state or location adjustment.
- TRACAB→2S conversion across seasons.
- Team totals including subs.

## Use in Second Wind
- Simulator: **validation target: the two teams' running totals in a match should correlate strongly (r ≈ 0.7)**. Our generator must make teams respond to each other (both teams run in the same phases), not draw totals independently.
- Fatigue estimator: none.
- Agents / claims: winners outrun losers only slightly (sprint +5%, ES 0.29; TD +0.7%, ES 0.22). "They won because they ran more" → **not supported**. "Teams that sprint more tend to finish higher" → **weakly supported** (rs .32, 2015–24) but see Allen2026b (r .25 in 2019–24).
- Overlay / UI: "both teams run together" chart: live running of both teams; fans see that one team's intensity pulls the other.

## Ideas or questions it raised
- The strong home–away correlation is a good "realism check" that judges understand.
