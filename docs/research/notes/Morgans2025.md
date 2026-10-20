# Morgans2025: EPL high-speed running and sprinting by possession, position and opponent ranking
Citation: Morgans R, Mandorino M, Beato M, Ryan B, Zmijewski P, Moreira A, Ceylan HI, Oliveira R. Contextualized high-speed running and sprinting during English Premier League match-play with reference to possession, positional demands and opponent ranking. Biol Sport. 2025;42(3):119-127. doi:10.5114/biolsport.2025.147011 (PMC12244393)
Type: match study (single club, 3 seasons)
Context: English Premier League, **one club** (first author affiliated with Brentford FC; the club is not named), seasons 2021/22 to 2023/24, all 114 league matches. 31 outfield players (age 24.6 ± 5.4 y): CB n=10, FB n=11, CM n=8, W n=5, CF n=7 (a player in several positions is counted in each). 1351 player-match data points (median 24.5 per player, range 1-114), of which 894 were "full or nearly full" matches (p.121). Team played 4-3-3 or 3-5-2, hybrid build-up/direct style, high press plus mid-block (p.120-121). Optical tracking: Second Spectrum, 25 Hz, all 20 EPL stadiums (p.120-121).
Evidence strength: medium. Recent, three seasons, many observations, same system as the current EPL provider. But one team, and **no table of means**: positional values are only shown as box plots and regression lines. Effect sizes are very large (ES up to 4.19), which looks inflated (pooled SD of per-minute IP values is small). Position is coded as an ordinal 0-4 predictor (CB=0, FB=1, CM=2, W=3, CF=4) in the regression, which is a statistical error for a categorical variable. So the "position β" values do not mean much.

## Definitions and thresholds
Journal pages (PDF page = journal page - 118).
| Metric | Threshold | Source |
|---|---|---|
| HSR | 5.5-7.0 m/s (19.8-25.2 km/h), **excludes sprint** | p.119, p.121 |
| SD (sprint distance) | > 7.0 m/s (25.2 km/h) | p.121 |
| IP / OP | own team in possession / opponent in possession. Ball-out-of-play distance is in neither | p.121 |
| Normalisation | "divided by the actual playing time for each player" → m/min of **total playing time**, not of IP or OP time (p.121). The paper does not state this precisely; this is my reading. |
| Ranking difference | league positions between the teams at the time of the match. Positive = own team ranked higher (better) (p.121) |
Inclusion: >= 75 min played, >= 80% of matches played, squad member at the start of every season (p.121). But 1351 data points include partial matches (median per player range 1-114), so the 75-min rule seems not to have been applied to all data. This is an internal inconsistency.

## Key numbers   (each with page/table/figure)
**In possession by position: medians (approx., read from Fig. 1, p.123), m/min of playing time; x 90 = approx. m per 90 (my calculation)**
| Position | HSR_IP m/min (IQR) | ≈ m/90 | SD_IP m/min (IQR) | ≈ m/90 |
|---|---|---|---|---|
| CB | ~0.8 (0.5-1.2) | ~70 | ~0.2 (0.1-0.3) | ~18 |
| FB | ~2.6 (2.0-3.2) | ~235 | ~1.1 (0.75-1.55) | ~100 |
| CM | ~1.7 (1.1-3.0) | ~155 | ~0.4 (0.2-0.7) | ~35 |
| W | ~4.1 (3.6-4.7) | ~370 | ~2.1 (1.6-2.65) | ~190 |
| CF | ~3.2 (2.8-4.1) | ~290 | ~1.5 (1.05-2.3) | ~135 |

Pairwise ES in possession (Fig. 1 legend, p.123; all p <= 0.01):
| Pair | HSR_IP ES | SD_IP ES |
|---|---|---|
| W vs CB | 4.19 | 3.30 |
| W vs CF | 0.81 | 0.65 |
| W vs FB | 1.64 | 1.42 |
| W vs CM | 1.93 | 2.63 |
| CF vs CB | 3.40 | 2.30 |
| CF vs FB | 0.85 | 0.64 |
| CF vs CM | 1.26 | 1.74 |
| FB vs CB | 2.44 | 2.06 |
| FB vs CM | 0.56 | 1.32 |
| CM vs CB | 1.26 | 0.70 |
Ranking: W > CF > FB > CM > CB for both HSR_IP and SD_IP.

**Out of possession: all positions pooled (approx., read from Fig. 2, p.124)**
| | HSR_OP m/min median (IQR) | SD_OP m/min median (IQR) |
|---|---|---|
| Home | ~3.5 (2.7-4.4) | ~0.85 (0.45-1.3) |
| Away | ~3.7 (3.0-4.8) | ~1.0 (0.6-1.5) |
| Home vs away ES | 0.24 (p = 0.01) | 0.23 (p = 0.01) |
Regression line HSR_OP vs ranking difference: ~4.4 m/min at -14 (playing a much better team) to ~3.2 m/min at +14 (playing a much worse team) (approx., Fig. 2a).

**Out of possession sprint distance by position: model lines (approx., read from Fig. 3, p.125), m/min**
| Position | slope per ranking place (text p.123) | SD_OP at Δrank = -14 | at 0 | at +14 |
|---|---|---|---|---|
| CB | -0.026 | ~1.6 | ~1.15 | ~0.8 |
| FB | -0.016 | ~1.75 | ~1.55 | ~1.3 |
| CM | -0.016 | ~1.4 | ~1.15 | ~0.9 |
| W | -0.001 | ~1.33 | ~1.25 | ~1.2 |
| CF | -0.001 | ~0.85 | ~0.78 | ~0.7 |
(Lines at 0 are my approximate readings. The figure's lines for W/CF look slightly steeper than -0.001.)

**Multilevel regression, Table 1 (p.122)**, β in m/min per unit (best models by AIC are in bold):
| Outcome | Position (ordinal) | Ranking diff (per place) | Away (vs home) | Pos x rank | Best AIC model |
|---|---|---|---|---|---|
| HSR_IP | 0.277 (p 0.001) | 0.011 (p 0.003, Model 2; n.s. later) | -0.042 n.s. | n.s. | **Model 1 (position only), AIC 1890.97** |
| SD_IP | 0.199 (p 0.001) | n.s. | n.s. | n.s. | **Model 1, AIC 1107.38** |
| HSR_OP | 0.100-0.122 n.s. | **-0.039 (p 0.001)** | **+0.369 (p 0.001)** | n.s. | **Model 2, AIC 2415.04** |
| SD_OP | -0.065 n.s. | **-0.023 (p 0.001)** | **+0.166 (p 0.001)** | **+0.005 (p 0.010)** | **Model 3, AIC 1513.69** |

Size of the context effects (my calculation from the β values):
- HSR_OP: from -14 to +14 ranking difference = 28 places x -0.039 = **-1.1 m/min** (about -30% of ~3.6 m/min), i.e. about -100 m per 90.
- HSR_OP away vs home: +0.37 m/min (about +10%), ~ +33 m per 90.
- SD_OP: 28 x -0.023 = -0.64 m/min across the full range; away +0.17 m/min.
- In-possession running is set by position. Out-of-possession running depends on context (opponent strength, venue).

**Approximate full-match sprint distance per position** (my sum of IP median + OP model line at Δrank 0; rough because it mixes medians with model means and leaves out ball-out-of-play, which is ~0.1 m/min in Kavanagh2024):
| Position | SD m/min | ≈ m/90 |
|---|---|---|
| CB | ~1.35 | ~120 |
| FB | ~2.65 | ~240 |
| CM | ~1.55 | ~140 |
| W | ~3.35 | ~300 |
| CF | ~2.3 | ~205 |
HSR_OP is not reported by position, so a full-match HSR per position cannot be built from this paper.

## Equations
Model structure (p.121; my notation; checked against PDF text, no equation is printed in the paper):
$$ y_{ij} = \beta_0 + \beta_{pos}\,\mathrm{pos}_{ij} + \beta_{rank}\,\Delta R_{ij} + \beta_{loc}\,\mathrm{away}_{ij} + \beta_{pos\times rank}\,\mathrm{pos}_{ij}\Delta R_{ij} + u_j + \varepsilon_{ij} $$
- $y_{ij}$: HSR or SD per minute (m/min) in IP or OP for player j in match i
- $\mathrm{pos}$: position coded 0-4 (CB, FB, CM, W, CF), treated as **ordinal** (statistically questionable)
- $\Delta R$: own league rank advantage over the opponent at match time (places; positive = own team better)
- $\mathrm{away}$: 0 home, 1 away
- $u_j$: random intercept per player; $\varepsilon$: residual

## Limitations
- One club with one tactical style (4-3-3/3-5-2, press plus mid-block). Context effects may be team-specific.
- No tables of means/SD; all values have to be read from figures.
- Ordinal coding of position makes the position β uninterpretable as a single number. The pairwise ES are more useful.
- ES values of 3-4 are unusually large and depend on the choice of pooled SD.
- Partial matches appear to be included despite the stated 75-min rule.
- The per-minute denominator (total playing time vs phase time) is not stated precisely.
- No acceleration data; no match status (score) control; no fatigue-related analysis (no time periods).
- Second Spectrum's filtering algorithms are not public (p.121).

## Use in Running Battery
- Simulator: per-position in-possession HSR and sprint rates (W > CF > FB > CM > CB). OP sprint rates by position and opponent rank. Add context modifiers: out-of-possession HSR falls ~0.04 m/min per place of rank advantage, and is ~0.37 m/min higher away. These give the simulator realistic **non-fatigue** reasons for running to vary.
- Fatigue estimator: important confounder. A drop in out-of-possession HSR can come from facing a weaker opponent (or playing at home), not from fatigue. The estimator should compare players against **context-matched** baselines, or at least use in-possession running (which is mostly set by position) differently from OP running.
- Agents / claims: the verifier should block "player X ran less out of possession, so he is tired" unless opponent strength/venue is accounted for. Allowed claim: "In one EPL team over 3 seasons, OP high-speed running fell as the rank advantage over the opponent grew, and was slightly higher away (ES ~0.24)."
- Overlay / UI: a "context" badge (home/away, rank difference) next to the battery.

## Ideas or questions it raised
- READING_LIST says "High-speed running by position, in and out of possession, by opponent". Imprecise: out-of-possession is **not** given by position for HSR (only pooled); sprint OP by position is only given as regression lines vs ranking. The study is one club, not league-wide. Opponent effect is a continuous "ranking difference", not opponent tiers.
- PLAN.md lists Morgans2025 as a source for "total ... distance per position". The paper reports **no total distance**.
- Fig. 3 shows CB sprinting out of possession falls most against weaker opponents (-0.026 m/min per place). A team that dominates spends less time defending in transition. The simulator's phase mix (how long each team defends) probably explains most of this. A good test of the simulator: does it reproduce these slopes without special rules?
- The HSR (5.5-7) band here excludes sprints, while Allen2024's HID (> 5.5) includes them. Always add SD when comparing.

Conversion quality: good for text; Table 1 is readable in md but the figures (the only source of positional values) are not converted, so figure values were read from the PDF images.
