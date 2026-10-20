# Allen2026b: "Possession in motion", running in and out of possession and success in the Premier League
Citation: Allen T, Taberner M, Zhilkin M, Harper D, Alexander J, et al. Possession in motion: a five-season analysis of running in-possession and out-of-possession with match outcomes in the English Premier League. Biol Sport 2026;43:899–909. doi:10.5114/biolsport.2026.159531 (open access)
Type: match study (league-wide, team-season level)
Context: EPL 2019/20–2023/24, Second Spectrum 25 Hz; 225 non-11 v 11 games removed → **1,675 games**, 26 teams, 1,196 players. GK included. Possession time and ball-in-play (BiP) from tracking. Analysis on **team-season averages** (one value per team per season).
Evidence strength: high for descriptive per-minute values; correlations are between-team, cross-sectional.

## Definitions and thresholds
- TIP = running during team in-possession time / TIP minutes; TOOP = running during out-of-possession time / TOOP minutes; TOOP/TIP ratio.
- Overall "/min" = total / match duration (stoppages included). TIP/TOOP exclude dead-ball time.
- Thresholds/dwell as Allen2024/2025 (HSR 5.5–7, HID > 5.5, SprD > 7 m/s; 0.5 s / 1 s).

## Key numbers   (each with page/table/figure)
- **Correlations with points per game (Table 4):** possession r = .74; TD TOOP/TIP ratio .65; HSR ratio .62; HID ratio .59; BiP .51; SprD ratio .50; HSR TOOP .45; HID TOOP .44; SprD TOOP .41; TD TOOP .34; **SprD total .25 (p = .010)**; HID .17 (ns); HSR .13 (ns); TD .04 (ns); SprD TIP −.22; HID TIP −.37; HSR TIP −.41; **TD TIP −.57**.
- **Per player-slot rates (Table 5, averages):** overall TD ~105–107 m/min, HID 8.2–8.7, HSR 6.3–6.6, SprD 1.8–2.0 m/min. **In possession: TD 130–136 m/min, HID 11.5–12.8, SprD 3.0–3.3. Out of possession: TD 142–148 m/min, HID 14.8–17.6, SprD 3.1–3.8.**
- Team-season ranges (Table 2): TD/min TIP 123.0 (Man City) – 142.8; TOOP 134.1–151.0; HID/min TIP 8.8–16.7, TOOP 12.8–20.0; possession 40–64%; **BiP 54–63% of match time**.
- Against top-six opponents (Table 5): possession −9 percentage points (ES −0.96 to −1.04); TOOP running/min lower (e.g. 7–20 teams HID TOOP 16.3 → 14.8, ES −0.39); total running/min slightly higher; BiP 55% → 58% for teams 7–20 (ES 0.62).
- Match length 96.4–101.2 min by season (Table 1).
- Authors: total running is now less linked to success than in Allen2026a; only SprD stays (Discussion).

## Derived (ours)
- Overall ~106 m/min while TIP/TOOP average ~139 m/min → with BiP ~57%, **running during dead-ball time ≈ 63 m/min** (106 = 0.57 × 139 + 0.43 × x → x ≈ 63). Derived, approximate.

## Equations
None.

## Limitations
- Team-season averages, so each correlation has ~100 points; between-team only.
- No game state, formation or location in the model.
- **Docling problems:** the .md starts mid-introduction (abstract lost) and Table 2 rows for Everton–Southampton are merged; Table 5 has blank cells. Abstract read from PDF.

## Use in Running Battery
- Simulator: **phase-specific running rates** (in possession ~133, out of possession ~145, dead ball ~63 m/min per player). Ball-in-play 54–63%. Out-of-possession HID/min > in-possession HID/min for most teams. Possession share and opponent strength shift these as in Table 5.
- Fatigue estimator: normalising by ball-in-play time (synthesis §3.4) is essential; TIP/TOOP per minute is the right denominator for comparing phases.
- Agents / claims: "Successful teams press harder out of possession (per minute) and run less with the ball" → **supported as association**. "Running more overall wins games" → **not supported** in 2019–24 (TD r .04).
- Overlay / UI: **pressing meter**: TOOP/TIP ratio live, with league range 0.99–1.23 (TD) from Table 2.

## Ideas or questions it raised
- TOOP/TIP is easy to compute from our synthetic data (needs possession labels). Good fan metric: "work rate without the ball".
