# Snyder2023: Which GPS metrics show fatigue in a soccer match simulation?
Citation: Snyder BJ, Maung-Maung C, Whitacre C. Indicators of fatigue during a soccer match simulation using GPS-derived workload values: which metrics are most useful? Sports 2024;12(1):9 (online 27 Dec 2023). doi:10.3390/sports12010009. PMC10818658
Type: experimental, repeated measures; each player is their own control; no control condition.
Context: 20 female NCAA Division I collegiate players (19.9 ± 0.8 y), USA, over two seasons, after an off-season block. Modified T-SAFT90 simulation on a 20 m course, 18 × 5 min segments with a 15 min half-time. STATSports Apex (GPS reported at 18 Hz, accelerometer 952 Hz) (p.2–3).
Evidence strength: **low**. Published in an MDPI journal, which our source rule excludes (READING_LIST); read as an exception on the user's request, 2026-10-17. Crossref checked 2026-10-17 (Sports, MDPI, 12(1):9, cited 7 times). Women collegiate players in a lab-style simulation, not professional men in matches, and there are several internal inconsistencies (below).

## Definitions and thresholds
- High-speed running (HSR): distance at ≥ 50% of the player's own 40-yard sprint max speed. Max speed 7.53 m/s (27.1 km/h, range 6.44–8.44), so the threshold was 3.76 ± 0.24 m/s (13.55 ± 0.87 km/h) (p.3). This is close to our 4.0 m/s "high-intensity" band, far below the 5.5 m/s HSR band.
- Accelerations / decelerations: counts of ≥ 0.5 m/s² held for 0.5 s (Table 1). A very low threshold.
- Speed intensity, dynamic stress load (DSL, accelerometer impacts > 2 g), total loading, fatigue index (DSL / speed intensity), step balance: STATSports proprietary metrics (Table 1).
- **Protocol changes from the validated T-SAFT90 (p.2–3):** the same commands in the same order every segment (identical demands), times per movement +7%, fewer running tasks, no jumps. After **every** 5-min segment, players walked to the lab for jump tests: **2–2.5 min away from the field each time**, so the whole protocol took up to 2.25 h. Planned distance 500 m per segment, 9,000 m in all.

## Key numbers   (each with page/table/figure)
- HSR per 5 min: 62.3 ± 48.2 m at 0–5 min, 49.1 ± 35 m at 15–20 min (p = 0.011), lowest 33.1 ± 22.1 m at 80–85 min (p < 0.001) (p.5, Fig. 2). That is −21% by minute 15–20 and −47% by minute 80–85 (derived).
- Max speed per 5 min: 22.54 ± 1.8 km/h (6.26 m/s) at 0–5, 21.58 at 15–20, lowest 20.43 ± 1.91 km/h (5.68 m/s) at 80–85: −9.3%, d = 1.15 (p.6, p.11). Each segment has only one commanded sprint on a 20 m course.
- Average speed: 6.35 → 6.03 km/h (−5%) by the last segment (p.6).
- Total distance per segment: 513 ± 15 → 494 ± 17 m (−3.8%, d = 1.21). The authors read this as players braking earlier and overshooting the cones less, not covering less of the course (p.7).
- Accelerations −31% by 20–25 min and −47% by 70–75 min; decelerations −36% and −59% by 80–85 min (p.10).
- Speed intensity −5.9% by 85–90 min (p.11).
- **Unchanged**: dynamic stress load, total loading, fatigue index, step balance (p.7). Jumps on a force plate: no change from baseline at any time (p.8–9).
- Heart rate 178 ± 9.5 bpm, about 92% of age-predicted maximum, flat after the first segment of each half (p.11). Higher than elite women in matches (169–173 bpm, Panduro 2022, cited p.11).
- Whole session: 9,050 ± 6.3 m and 876 ± 10.4 m HSR (p.10).

## Equations
None (manufacturer definitions in Table 1).

## Main message
When the running is **imposed** (fixed commands, players told to follow them exactly), speed-based metrics fall from minute 15, much earlier than in real matches, where most studies see the drop only in the last 15 min (p.10–11). The authors read this as indirect evidence that players **pace themselves** in real matches (p.11). They also say fatigue "may be as much a function of intensity over a short period of time as it is of accumulated work" (p.11).

## Limitations and errors (read critically)
- **MDPI journal**; small n (20); women collegiate players; no control condition.
- **The protocol is not continuous.** A 2–2.5 min break after every 5 min (p.3) is long enough to refill much of a fast energy store, so the time course doesn't map onto a 90-min match. The modified protocol is also not the one validated against match play.
- **Internal inconsistencies** (all present in the PDF, not conversion errors):
  - Accelerations "reduced from T0–5 (5.40 ± 2.7) beginning at T15–20 (7.45 ± 3.0)" (p.7): the values go up, so they are probably swapped.
  - Table 3's ACC row is an exact copy of the Max Speed row (p.9).
  - The text says max speed fell significantly at 15–20 min (p = 0.019, p.6; d = 0.6, p.11), Table 3 says not significant there. Average speed: text says lower from 25–30 min, Table 3 says not significant at 25–30 and 40–45.
  - The abstract says accelerations fell from 15–20 min; Table 3 says not significant at 15–20.
  - The session SDs (9,050 ± 6.3 m; HSR 876 ± 10.4 m) are implausibly small next to the per-segment SDs (± 15 m and ± 22–48 m), so they are probably standard errors or typos.
- About 15 segments × 11 metrics compared with paired t-tests, with no correction for multiple comparisons stated (p.5).
- Max speed comes from a single commanded sprint on a short course every 5 min, so the decline may partly be effort, not capacity.
- Acceleration counts at 0.5 m/s² are not comparable with any match study (the authors say so, p.10).

## Use in Running Battery
- **Simulator**: no calibration target (wrong population, not a match). It supports leaving our generator **without pacing** only as a known simplification: real players spread their effort, so the real fade is gentler and later than an imposed one. Our targets already come from matches (Bradley2009), so they include whatever pacing real players do.
- **Fatigue estimator**: two points.
  1. Pacing hides fatigue in the output. In a match the player chooses how hard to run, so a tired player running less looks like a player choosing to run less. This is one more reason the behaviour cues we found are weak (next-minute high-speed running effect size about 0.1, PLAN §3.3) and why we report the work done, not who is tired.
  2. "Intensity over a short period" as well as accumulated work: consistent with our split into a battery (recent hard running) and a tank (whole-match load).
- **Agents / claims**: accelerometer metrics (DSL, total loading, fatigue index) didn't respond, but we don't have accelerometers anyway. Explosive power (jumps) was preserved, which agrees with "intense accelerations are not suppressed after peaks" [Leifsson2024] and supports blocking "he can't accelerate any more" (claim 23). A qualified claim about pacing is possible in analyst mode (synthesis §5.2, 19d).
- **Overlay / UI**: none.

## Ideas or questions it raised
- Our synthetic matches have no pacing, so on synthetic data the late fade comes only from physiology. On real data some of it is choice. That makes the synthetic validation slightly optimistic for any "fade" signal; worth one line in the README limitations.
