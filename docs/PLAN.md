# Second Wind: Project Plan

> The story the scoreline doesn't tell: who's running on empty, and when it costs them.

Citations like `[Leifsson2024]` refer to keys in [READING_LIST.md](READING_LIST.md). Page, table and figure references for every number are in [RESEARCH_SYNTHESIS.md](RESEARCH_SYNTHESIS.md), cited here as "synthesis §x".

**Deadline:** October 27, 2026, 11:59 pm Pacific Time.

**Updated 2026-10-16** (estimator built: §3.3 "As built", decision 12). The research phase finished on 2026-10-14 (64 papers) and the open decisions are settled (section 7). The build plan is in [BUILD_PLAN.md](BUILD_PLAN.md).

---

## 1. The idea in one paragraph

We build a synthetic match generator in which player fatigue really affects play. A fatigue model, based on published sports science, then estimates each player's energy from movement data alone: speed, acceleration and distance. AI agents spot moments where fatigue mattered, explain them in plain English, and adapt the output for casual fans and for analysts. A live overlay shows a "battery" for each player during the match.

---

## 2. Data strategy

### 2.1 What the rules require

- Section 4.7: *"Projects must use synthetic, football-realistic data."* No data is provided, so **we generate it**.
- Section 4.1 (v) lists "create or extend synthetic football-realistic datasets" as a feature, and the judging asks about "optimized synthetic data creation." The generator is part of what gets judged, so it is worth doing well.
- Section 7 gives Microsoft a commercial license to our submission, so anything in the repo must be ours or under a permissive license.

### 2.2 Open data: what exists

We use real open data **only offline, to calibrate and validate the generator**. The demo runs on synthetic data only, and the repo only contains fitted parameters (numbers), not the real data.

| Dataset | What | License | Use for us |
|---|---|---|---|
| **IDSSE / Bassek et al. (2025)**, *An integrated dataset of spatiotemporal and event data in elite soccer*, Scientific Data. [paper](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11787359/) | 7 matches from 2022/23: 2 Bundesliga and 5 2. Bundesliga, all Fortuna Düsseldorf home games. TRACAB 25 Hz tracking of all players and the ball, plus events. **Events are not synchronised** with tracking in the release: offset −0.37 ± 1.82 s, max 27 s [Bassek2025, p.8]. | **CC BY 4.0** | **Speed and acceleration distributions only**, and a test bed for our pre-processing. Not for fatigue patterns over a match: 7 matches with one home team is too few and too skewed (synthesis §7.5). Load with **floodlight** (`io.dfl`), as the paper does [Bassek2025]. |
| **SkillCorner Open Data** [github](https://github.com/SkillCorner/opendata) | 10 matches, broadcast tracking (only players visible on camera). | **MIT** | Second source for movement calibration. Broadcast tracking reads top speed about 0.6 m/s (2.1 km/h) **lower** and total distance about 400 m higher than TRACAB [Castellano2025, Methods 2.3]. Correct for this before comparing. |
| **Wyscout public dataset** (Pappalardo et al., 2019, Scientific Data) | Events for a full season of 7 competitions **including the Premier League 2017/18**. No tracking. | **CC BY 4.0** | Event rates and patterns: passes per minute, pass lengths, shots, tackles. Premier League-specific. |
| **StatsBomb Open Data** [github](https://github.com/statsbomb/open-data) | Events for many competitions, some with "360" freeze frames. | Custom terms: attribute StatsBomb + logo | Optional extra event calibration. |
| **Sutcliffe & Kramer (2025) raw data**, Harvard Dataverse, doi:10.7910/DVN/5FTIRQ | 26 university players: 3-minute-test CS and D′, plus match GPS at 10 Hz [Sutcliffe2025]. The public file is **one summary spreadsheet** (15 KB, per-match D′-balance summaries), not raw GPS (checked 2026-10-14). | **CC0** | Compare our battery's dips (e.g. 21 ± 6% of D′) with real players' summaries. We cannot run our estimator on it. |
| **Metrica Sports sample** [github](https://github.com/metrica-sports/sample-data) | 3 anonymized matches, tracking + events. | No formal license ("be responsible, acknowledge") | Prototyping only. Don't rely on it. |
| **PFF FC World Cup 2022** [blog](https://www.blog.fc.pff.com/blog/enhanced-2022-world-cup-dataset) | 64 matches, tracking + events. | Unclear, behind a form | Skip unless terms are clear. |

Python tools to load them: **floodlight** (IDSSE, as in [Bassek2025]), **kloppy** (check whether its Sportec/DFL loader reads IDSSE), **databallpy**.

> ⚠️ This is our reading of the rules (section 4.7 asks for synthetic data; we use open data only offline, to fit numbers). Decided 2026-10-14 not to ask the organizers.

### 2.3 How we generate realistic data

**Approach: our own simulator, calibrated on open data and published numbers.** We considered Google Research Football (Apache-2.0, has a built-in "tired factor") but its fatigue model isn't research-based, and it's a heavy game engine. Writing our own gives us full control, and the generator itself is something to show the judges.

The simulator has three layers:

1. **Match flow (events).** A state machine of phases of play: build-up, progression, final third, positive transition, negative transition, high press, set piece, ball out. Each phase emits events (pass, carry, reception, shot, tackle, pressure, interception…) at rates fitted on the Wyscout Premier League data.
   - Every frame records whether the ball is in play and which team has it.
   - A match lasts **99.5 ± 2.9 min** including added time, not 90 [Allen2025, Table 2].
   - Both teams' running comes from a shared match tempo, not drawn separately: the two teams' totals move together, r = 0.68–0.75 [Allen2026a, Fig. 2].
2. **Movement (tracking, 10 Hz).** Each player has a target position from formation + phase + ball position (team shifts, pressing, recovery runs). Players move toward it with a sprint motion model [Narizuka2023], limited by each player's own acceleration–speed profile (A0, S0) [Morin2021, Table 1].
3. **Hidden physiology (the ground truth).** Each player has a "true" CS, D′, A0, S0 and recovery speed, with individual variation (synthesis §3.2.3).
   - **Short-term store: two pools.** A fast pool (about 40–50% of D′, recharge time about 15–35 s) and a slow pool (about 50–60%, about 400–500 s when walking) [Chorley2022; Chorley2023, Eq. 6b–6c; synthesis §3.2.4].
   - **Whole-match "tank".** Falls with total energy used; partly resets at half-time; a dip in the first 5–10 min of the 2nd half [Bradley2013; Mohr2005]. The sizes are our choice, calibrated to synthesis §3.5.
   - **What low energy changes: fewer, shorter, slightly slower hard runs, plus skipped covering and recovery runs.**
     - Hard runs after a peak spell: length −23% (19.2 → 14.8 m), duration −32%, mean speed −3% (6.33 → 6.14 m/s [22.8 → 22.1 km/h]), all vs the peak 5 min [Fang2024, Table 2].
     - Covering runs −22 to −44% and Recovery Runs −34 to −43%, both vs the player's own match average [Ju2022, p.975]. (The paper's "20–53%" mixes these player figures with team figures.)
     - Carries are fewer, shorter and slower; players receive the ball at lower speed (ES −0.32, −0.37, −0.5) [Fang2024, Fig. 1].
   - **Capacity loss is capped at about 5%** for maximum speed and acceleration by the end of the match. Match top speed barely changes: 7.65 vs 7.59 m/s (27.5 vs 27.3 km/h), not significant [Bradley2009, p.163]. Sprint tests are only about 3.5% slower after a match [SilvaJR2018, Table 5].
   - **Intense accelerations are not suppressed after peaks.** Acceleration distance is higher after acceleration peaks [Leifsson2024, Table 1].
   - **Passing: no accuracy penalty.** Pass completion was 80.3% before a peak and 80.5% after [Fang2024, Fig. 1], and 66–71% in every 15-min block [Carling2011, Table I]. No ball-speed penalty in v1: the only evidence is a lab test with youth players [Russell2011, Table 1].
   - **Recovery after intense spells** is calibrated to Leifsson2024: high-speed running after a 5-min peak is −45, −29, −13, −8 and −4% vs the match average in minutes 1–5 [Leifsson2024, Table 1].
   - **Every run gets an intended purpose** (Recovery Run, Covering, Close Down… the 11 classes in [Ju2022]). Runs a fresh player would have made but a tired one skipped are logged too.
   - **As built (2026-10-16; `sim/physiology.py`, values and sources in `sim/params.py`).**
     - Pools: drain above CS in proportion to what each holds; refill below CS with Chorley2023's τ curves (Eq. 6b–6c, speed for power: our adaptation), scaled to each player's τ at rest; the slow pool refills up to +60% slower as the tank empties [Chorley2022]. The pools refill over the 15-min half-time [IFAB2025, Law 7].
     - Tank: falls with metres run above CS and gets back half its loss at half-time (our assumption, calibrated to the end-of-match decline). Dip: 10% fewer hard runs at the second-half kick-off, gone after 10 min (our assumption) [Bradley2013; Mohr2005].
     - Behaviour: a hard run (wanted above 4 m/s) is skipped with chance 1 − run choice, where run choice = pool term × tank × (1 − dip). The pools only count below 75% of D′. The tank does not cut decisive sprints (runs in behind, tracking, counter support), so sprinting stays about level between halves [Bradley2009, p.162]. Short-term tiredness also shortens and slows runs and carries a little [Fang2024]. Capacity: top speed and acceleration fall with the tank, at most 5%. No passing or ball-speed penalty (decision 5).
     - **Two truth labels** (decided 2026-10-16, revised the same day; schema 0.1.4). Each is where its part of the hidden state alone cuts the chance of a hard run by at least a quarter (our assumption, at the low end of Ju2022's 22–45%).
       - **Tired moment** (`truth.json` `tired`): the pools alone (short-term tiredness after intense spells), what the estimator's battery and post-peak flag look for. About 5% of outfield player-seconds, a few short spells per player and match.
       - **Late-match fatigue**: the tank below 0.75 (`settings["late_tank_below"]`, read from the `tank` series). None before the 30th minute, about half of the last 15 min; players with the lowest CS most, since all positions share one work rate (no pacing to capacity, decided 2026-10-16; revisit after the validation batch).
       - A single label on run choice (< 0.75) was tired a third of the time and two thirds of the last 15 min, so precision and recall would have been easy to inflate late in matches. Tired-moment precision and recall are scored on the first label; late-match fatigue is scored as a trend against the estimator's whole-match load.
     - **Skipped runs** in `truth.json` (schema 0.1.4): one per situation (a shape run asked again 5 s later and skipped again is the same skip), and only those forecast to have been high-intensity runs (above 5.5 m/s for 1 s or more, `movement.forecast_hi_run`), so they count like the measured runs that were made. Only about 40% of hard-run decisions that are made become measured high-speed runs, so logging every skipped decision overstated the skips about 2.5 times. The forecast agrees with the measured outcome for about 3 made decisions in 4 and is unbiased overall (our measure, 30 seeds).
     - **Fatigue switch** (decided 2026-10-16): fatigue on by default; `--no-fatigue` is the no-fatigue control (same seed, teams, physiology, tempo and work rates); `--no-fatigue --no-tempo` also switches back to the fatigue-off calibration (`params.PRE_FATIGUE`) and reproduces the generator before this change (81f023d) file for file on one machine.
     - **Work rate re-fitted with fatigue on** (the totals of real matches include fatigue), and two run chances raised (overlaps, midfield support), since a skipped one-off run is not offered again.
     - **Shared tempo**: one per match, N(1, 0.03), scales both teams' work rate in play [Allen2026a].
     - **Substitutions** (decided 2026-10-16; schema 0.1.5; `--no-subs` to leave them out): 3–5 per team, in up to three windows around 58, 71 and 81 min, an early one at half-time [IFAB2025, Law 3; Myers 2012 and Bradley 2014 via Hills2018, Table 1]; like for like, attackers and midfielders more often than defenders (weights our assumption). Planned before kick-off from their own generator, so the no-fatigue control makes the same ones; made at the first stoppage after the planned time. The substitute takes over the slot where the player stood (no walk off and on: our simplification), fresh, with their own hidden values and no extra work rate. Position totals are per slot (starter plus substitute), like the targets (synthesis §4.2). The published-comparison checks (end of match, post-peak, purposes) use whole-match players only, as the papers did; substitutes get their own check against Bradley2013 and Hills2018.
     - The no-fatigue control already shows most of the published post-peak drops (selection and stoppages, section 2.5), so the effect sizes are calibrated on the end-of-match decline and on what tired players skip, and the post-peak curves are reported with and without fatigue (`sim.fatigue_checks`).

**Story controls.** Seeded parameters to create interesting matches on demand: "Team A presses high for 60 min then fades," "the left-back is exposed by repeated counterattacks," "a fresh substitute makes the difference."

**Output format** (full schema in synthesis §7):
- `events.jsonl`: one event per line: id, time, period, type, subtype, player, team, start and end location, outcome, possession id, **phase** label, score state. Types include **carry** (start and end) and **reception**, so carry speed and receiving speed can be computed [Fang2024].
- `tracking.jsonl`: one frame per line (10 Hz): time, period, **ball in/out of play**, **team in possession**, ball x/y/z, and x/y for 22 players. Realistic position noise (white, σ = 0.05 m per axis, plus dropouts; synthesis §3.1 and `sim/params.py`). Speeds are optional; the estimator recomputes them from positions.
- `metadata.json`: teams, line-ups, formations, positions (GK, CB, FB, DM, CM, AM, WM, CF, as in [Allen2024]), substitutions, fictional names and clubs. Optional per-player **club test values** (CS, D′, A0, S0): the truth plus measurement error, written only for the club-data experiment (generator flag `--club-tests`, section 3.2). Broadcasters never have them.
- `truth.json`: the hidden "true" fatigue per player per second: fast pool, slow pool, tank, capacity multipliers, the **intended purpose of each run**, skipped runs, and true tired-moment labels [Fang2024; Ju2022; Allen2026b]. **Only for validation, never given to the estimator.**

Follow an existing event schema (e.g. SPADL or StatsBomb-like) so it looks professional and other tools can read it.

### 2.4 Why the ground truth matters (our strongest rigour point)

Because we generate the data, we know the "true" fatigue. So we can **measure how good our estimator is**, something nobody can do with real matches, where fatigue is never measured directly.

To avoid a circular argument (testing the model against itself), the simulator's physiology is **different and richer** than the estimator's:
- **Truth:** two pools, a whole-match tank, individual parameters, and behaviour rules (section 2.3).
- **Estimator:** one D′ balance plus metabolic power, from positions only (section 3).

This does **not** remove every circle. The behaviour rules (tired players make fewer and shorter hard runs) come from the same papers the agents will cite, so finding them in our data is true by construction. Section 2.6 sets out how we check the data against real matches and how we report this limit.

Stretch goal, **cut unless time allows**: a second, structurally different truth model (three-tank hydraulic [Weigend2023]) to show the estimator copes with model mismatch. Its equations are in Weigend 2021, which is not in our set, and fitting takes at least 3 h per CS/D′ pair [Weigend2023, §4.2].

### 2.5 Realism check

We compare synthetic matches against published numbers and open data, and show the comparison in the README. Pass thresholds are our proposals (synthesis §6.1).

**Priority (added 2026-10-15):** the movement rows (distance, sprints, speed and acceleration distributions, running by phase, post-peak curves) come first, because they are what the estimator reads. Event counts are a secondary check: they shape the match flow but the estimator never uses them (section 2.6).

| Check | Target | Source |
|---|---|---|
| Distance per position | 2024/25 targets, ±5%. Example: CB total distance 9,830 m, sprint 140 m; WM 10,870 m, sprint 340 m (full table in synthesis §4.2) | [Allen2024, Table 4, p.782] scaled to [Allen2025, Figs 2–3] (derived) |
| Team totals per match | Total distance 113,891 ± 4,097 m; high-speed (>5.5 m/s [19.8 km/h]) 9,611 ± 1,300 m; sprint (>7 m/s [25.2 km/h]) 2,326 ± 471 m | [Allen2025, Figs 2–3] |
| Match length | 99.5 ± 2.9 min | [Allen2025, Table 2] |
| **Sprint counts per position** | Sprints >6.94 m/s (25 km/h), ≥0.7 s, per 98 min: CB 7.2, FB 12.7, CM 8.8, W 14.0, FW 13.2. Pass if within ±30% (different tracking system) | [Castellano2025, Table 3] |
| **Two teams move together** | Home and away team totals correlate at r = 0.68–0.75. Pass if r is 0.5–0.85 over ≥50 synthetic matches | [Allen2026a, Fig. 2] |
| **Running by phase** | About 133 m/min in possession, 145 out of possession, 63 during stoppages, per player slot. Pass if each is within ±10% | [Allen2026b, Table 5]; stoppage value derived |
| Ball in play | 50–63% of match time | [Kavanagh2024, p.80; Allen2026b, Table 2] |
| Speed and acceleration distributions | IDSSE resampled to 10 Hz; time in each speed band within ±3 percentage points | [Bassek2025; Osgnach2010, Tables 1–2] |
| Events per match | Wyscout Premier League; IDSSE about 740 passes and 24 shots per match. Within ±15% | [Bassek2025, Table 1, Fig. 3] |
| **Post-peak curves (main target)** | Leifsson high-speed and sprint curves after 1-, 2- and 5-min peaks. Each minute within ±10 percentage points; minute 1 after a 5-min peak between −35 and −55% | [Leifsson2024, Table 1] |
| Accelerations after peaks | Not suppressed | [Leifsson2024, Table 1] |
| **When peaks happen** | High-speed peaks spread evenly within each half (KS test p > 0.05). Total-distance and acceleration peaks start early (median < 15 min into each half). The 1-min high-speed peak lies inside the 2-min peak in <30% of cases | [Thoseby2022, Tables 1–2] |
| **End-of-match decline** | Running >4 m/s (14.4 km/h): last 15 min 10–30% below the first 15 (published −21%). High-speed and sprint per half within ±10%. Recovery time between hard efforts up 15–40% (published +28%). Total distance per minute lower in the 2nd half; sprint per minute flat | [Bradley2009, Fig. 2, p.162–163; Chen2025] |
| **Substitutes** | High-speed running per minute above whole-match players: +15% like for like over the same period [Bradley2013, Table IV], +27% against the whole match (12.4 vs 9.8 m/min) [Bradley 2014 via Hills2018] | synthesis §4.7 |
| **No-fatigue control match** | See below | synthesis §6.2 |

**No-fatigue control match.** Picking each player's most intense window guarantees lower values afterwards, even with no fatigue at all. Play also stops after peaks: ball in play falls from 82% to 57% in the minute after a peak [Cortez2026, Table 3]. So:
1. Generate the same matches (same seeds and tactics) with fatigue **switched off**.
2. Run the exact Leifsson2024 and Ju2022 pipelines on both sets.
3. Show three curves side by side: published, synthetic with fatigue, synthetic without fatigue.
4. Calibrate so the with-fatigue curve matches Leifsson2024. The gap between the two synthetic curves is the part that is really fatigue.

No published study controls for this, so it is our strongest rigour slide.

**First result (2026-10-16, `sim.fatigue_checks`, 240 seeds).** In our generator the control *without* fatigue already drops as much as Leifsson2024's published curve, or more: −63% in minute 1 after a 5-min HSR peak (−67% with fatigue) against −45% published. Our peak intensities are a little higher than the published ones (1-min HSR peak 73 vs 62 m/min). So the fatigue part after peaks is small, and step 4 cannot be met: the with-fatigue curve sits beyond the published one. We report all three curves as they are and calibrate the effect sizes on the end-of-match decline instead.

### 2.6 Making the synthetic data credible (added 2026-10-15)

A review of synthetic data in sport warns that such data can be "statistically plausible yet practically misleading". Its checklist asks how models built on synthetic data behave on real or held-out data, and whether analyses reach the same conclusions on both [RuizPinto2026, Introduction; Table 2, RQ2; Table 3]. A soccer player-detection dataset built from a simulator with simple rules (no offside) was useful because it was tested on two real datasets, and because it deliberately randomised what the simulator could not get right [Qin2025, §2.1–2.2, Table 1; arXiv preprint]. What our synthetic data can show: the estimator recovers a hidden fatigue state **under the effects we built in**. What it cannot show on its own: that those effects, or the estimator's outputs, hold in real matches. Five measures:

1. **Same conclusions on real data (IDSSE, 7 matches).** Run the estimator offline on the real IDSSE matches [Bassek2025] (CC BY 4.0, calibration only, never in the demo). There is no fatigue truth there, so we compare conclusions, not accuracy: post-peak drops, second-half decline, and the distributions of battery drops and tired-moment rates, real against synthetic. Where they disagree, we say so in the README.
2. **Realism checks aimed at what the estimator reads.** Speed and acceleration distributions, sprint counts and high-speed running per position against IDSSE and synthesis §4.2 come before event counts (section 2.5).
3. **Randomised assumptions across the validation batch.** Each of the 50 matches draws its own fatigue effect sizes, pool settings (including values outside the estimator's priors), position noise and team tempo. We report estimator accuracy across that whole spread, not at one setting. This is a cheap stand-in for the cut second truth model (section 2.4). *As built (2026-10-16):* `--vary` (`params.VARY`, `VARY_PLAYERS`, recorded in truth.json `settings`); the validation batch is seeds 1001–1050, natural matches only, in `data/synthetic/validation/` (git-ignored; regenerate with `seq 1001 1050 | xargs -P 25 -I{} uv run python -m secondwind.sim --seed {} --vary --out data/synthetic/validation/v{}`). The truth labels are not varied.
4. **Natural matches and story matches kept apart.** Story controls deliberately over-represent tired moments, which is a class-imbalance choice [RuizPinto2026, Structure]. Tired-moment precision and recall are reported on natural matches only; story matches are for the demo.
5. **A synthetic-data card in the README**, one short paragraph per checklist dimension: objective, structure, generation, constraints, utility and fidelity, risk and deployment [RuizPinto2026, Table 3]. It states the limit in plain words: "this shows the estimator recovers fatigue under the published effects we built in; it does not prove those effects in this league."

---

## 3. Fatigue model (estimator)

Input: tracking data only (positions over time), plus ball status and possession. Output: per player, per second.

### 3.1 Pre-processing

- Zero-lag 4th-order Butterworth low-pass filter at **1 Hz** on x and y, then central differences for speed and acceleration [Deutsch2025, Methods].
- Check on IDSSE whether a 1–2 Hz cut-off keeps short accelerations.
- Use tangential acceleration (the rate of change of speed) for metabolic power.
- Sanity caps: speed 12 m/s (43.2 km/h), acceleration 10 m/s² (synthesis §3.1).

### 3.2 Player settings: CS and D′ in two modes

- **CS (critical speed)** is the fastest speed a player can hold for a long time without draining their short-term reserve.
- **D′** is the size of that reserve: the extra distance, in metres, a player can cover above CS before slowing down.
- Fitting CS from match data does not work: it comes out at about 2.0 m/s (7.2 km/h), a jog [Mizelman2024, Table 3, p.2064].
- Broadcasters don't get clubs' fitness tests, so the default mode uses only what a broadcaster has.

| Mode | CS and D′ come from | Who it fits |
|---|---|---|
| **Broadcast (default)** | One prior for all outfield players: CS 3.7 m/s (13.3 km/h), D′ 180 m [Sutcliffe2025, Fig. 2; Liu2021, Table 4; synthesis §3.2.3]. **Per-player update from match data** (decision 9): each player starts from this prior and is narrowed by what they actually run. Fallback: the one-way correction (if the battery would drop below zero, raise D′ to fit what the player did; never lower D′ or move CS). | Fans, TV, the league |
| **Club data (validation experiment only)** | Club test values (truth plus measurement error, written only with `--club-tests`), plus the same correction | Nobody in the product: it measures how much club data would add |

- **Decision 2026-10-15: broadcast is the only product mode.** Broadcasters and the league never get clubs' fitness tests, and few clubs test CS and D′ for the whole squad. Club test values are left out of `metadata.json` by default and used in one validation run. Their error is normal: A0 5.4% and S0 3.3% [Morin2021, Table 1]; CS 5% and D′ 15% (our assumption; D′ depends strongly on the method, synthesis §3.2.3).
- Position differences come from role behaviour, not from different settings. No paper gives CS or D′ by position (synthesis §3.2.3).
- Validation runs both modes against the truth, to show how much accuracy is lost without test data.
- **Decision 2026-10-15: per-player update of CS and D′ (synthesis §3.2.5, option C, light version).**
  1. Draw about 200 (CS, D′) pairs per player from the prior: CS 3.7 ± 0.25 m/s, clipped to 3.2–4.2; D′ 180 ± 54 m, clipped to 100–300 (synthesis §3.2.3; the SDs as in `sim/params.py`). k stays fixed within a run, so the k sensitivity runs still mean something.
  2. Run the battery for every pair at once.
  3. Down-weight pairs that the player's running contradicts (their battery goes well below zero), with a soft penalty rather than a cut-off. The penalty width is our assumption, tuned in validation.
  4. Show the weighted median battery with a 10–90% band.
  - Match data mostly gives a **lower bound** on capacity: players rarely run themselves empty (deepest dip 21 ± 6% of D′ [Sutcliffe2025, Fig. 3]), and fitting CS from match data alone gives about 2 m/s [Mizelman2024, p.2064]. So for most players the updated values stay close to the prior; the main gain is an honest band per player.
  - Validation reports the band's coverage against the hidden truth (synthesis §6.3, 80% target). The validation batch must draw some true values outside this prior (section 2.6, point 3); otherwise the test flatters the estimator.
  - The one-way correction stays in the code as the fallback if this slips.
  - Roadmap, not built: carry each player's updated values into their next match as the new prior, so the band narrows over a season.
  - **As built (2026-10-16; `engine/battery.py`, values in `engine/params.py`).** Every draw runs its own battery with the one-way correction; a draw whose D′ had to be raised keeps exp(−½ (raise / (0.1·D′))²) of its weight (width our assumption). Weights use the running so far only, so the battery works live. On default matches (seeds 1–60) the update learns almost nothing, as expected: estimated vs true D′ r = 0.03, CS r = 0.05; widths 0.05–0.4 move the battery by less than 0.001.

### 3.3 Signals

| Signal | Method | Source |
|---|---|---|
| **Battery (short-term)** | D′ balance: drains by (speed − CS) metres per second above CS. Below CS it recharges with recharge time τ = k·D′/(CS − speed), **k = 4**, clipped to 30–900 s. Sensitivity runs at k = 1, 3 and 5. With default settings, τ ≈ 195 s standing and ≈ 330 s walking (derived). **A relative gauge only**: "lowest point of his match", "lower than his teammates", never "empty" or "exhausted". | [Skiba2021; Jones2017, p.S76]. The standard form (k = 1) recharged about 5× too fast in runners: 68 s vs 362 s fitted [Bellenger2025, p.721–722, Figs 2–4] |
| **Load (whole match)** | Metabolic power from speed **and** acceleration. Report rolling 1- and 5-min averages and total energy; never "distance above 20 W/kg". | [Osgnach2010; diPrampero2005]; zone distance varies 73.6% between trials [Buchheit2015, Table 2] |
| **Recent intensity** | Rolling 1-, 2- and 5-min high-speed distance compared with the player's own peak curve. "Post-peak" flag for about 2 min after a 1–2-min peak and about 5 min after a 5-min peak. Rates per ball-in-play minute. Tracks high-speed running separately from total distance. | [Leifsson2024, Table 1; Thoseby2023, Table 2; Fang2024] |
| **Effect on play** | Pitch control, Spearman/Shaw model as used by da Silva: σ 0.45 s, λ 4.3 s⁻¹ [Spearman2017, p.7]; reaction time 0.7 s, goalkeeper λ 12.9 s⁻¹, ball speed 15 m/s (54 km/h) [daSilva2025, p.3]; κ = 1. Computed from **actual positions** at event moments (or 1–2 Hz), so a skipped recovery run shows up directly. A "fresh" version is shown only as a labelled model estimate. | [Spearman2018, Eq. 3–4; daSilva2025] |
| **Confidence** | Every number is an estimate with a band. The battery band comes from the per-player update (decision 9); its coverage is checked against the truth, and the band is widened if coverage falls short. Floor is the 7–20% typical error of D′ estimates. Fan mode shows a 5-level battery icon. | [Skiba2021, p.1567; Buchheit2015] |

**Not built: capacity check (acceleration–speed profile).** One match doesn't give a reliable profile: match-only A0 vs a sprint test ICC 0.23 [AlonsoCallejo2024, Table 2]. Its noise (A0 5.4% [Morin2021, Table 1]) is larger than the 2–4% loss we would be looking for [SilvaJR2018, Table 5; Krustrup2006, p.1171]. A0 and S0 stay as simulator limits and metadata values. If time is left over: a post-match, half-vs-half analyst view labelled "low confidence".

**Tired moment detection.** *(Revised 2026-10-16, decision 12: battery only; the post-peak flag is a separate signal.)* A defensive action (duel, recovery run, pressure) by a player whose battery is low **for them**, or who is inside a post-peak window. Scored against the short-term truth label (`tired`); late-match fatigue (the tank) is a separate trend, compared with the load signal (section 2.3, "Two truth labels"). Losing the ball (negative transition) gives the hardest running of the game for total distance [Bortnik2022, Fig. 3; one Polish team, GPS], so it is the first place to look. The main pattern the agents explain: in the Premier League, after a peak spell, players do 22–44% less Covering and 34–43% less Recovery Running than their match average [Ju2022, p.975].

**As built (2026-10-16; `secondwind.engine`, output `signals.json`, schema 0.1.6).** `uv run python -m secondwind.engine <match folder>`; estimator vs truth for one match: `uv run python -m secondwind.validate.estimator <match folder> --plot chart.png`.
- Per player, per second on the pitch: battery with 10–90% band; metabolic power (1-s, 1-min and 5-min means) and energy since kick-off; high-speed distance (>5.5 m/s [19.8 km/h]) in the last 1, 2 and 5 min, also as a share of the player's reference peak; share of each window with the ball in play; red-zone and post-peak flags; tired flag. Tired spells list the player's defensive actions and ball losses inside them.
- Red-zone spell: a full window at ≥ 90% of the player's best so far and of the published mean peak (62 / 38 / 22 m/min for 1 / 2 / 5 min [Leifsson2024, Table 1]); post-peak lasts 2 min after a 1- or 2-min spell, 5 min after a 5-min spell, and ends at half-time.
- **Tired moment = battery below 50% of the player's estimated D′.** Dev seeds 1–60, outfield player-seconds, against `tired`: precision 0.30, recall 0.10; as spells (matched within 30 s) precision 0.44, recall 0.15, about 42 spells per match. The target (precision ≥ 0.7 at recall ≥ 0.5, synthesis §6.3) is out of reach from positions: the same battery with the true CS and D′ gives 0.57 / 0.45, with club test values 0.38 / 0.45. Tiredness is concentrated in low-capacity players (the top 10% of players hold 65% of tired seconds; tired share vs true D′ r = −0.45, vs CS r = −0.36), and positions cannot tell who they are. Battery vs hidden pools: mean absolute error 0.069, r 0.70, band coverage 73% (target 80%).
- Load sanity check (validation match v1001, whole-match outfield players): energy 60.8 kJ/kg (published 61.1 ± 6.6 [Osgnach2010, p.174]), mean 10.0 W/kg (about 10.7, synthesis §2.3).

### 3.4 What the agents may claim: the Verifier's rulebook

The Verifier uses the claims register in synthesis §5 as its rulebook. Key rules:
1. **Every percentage says what it is compared with**: "vs his match average", "vs his peak", "vs the first 15 min". Figures like −93% or −77% are vs the peak, never "below normal" [Cortez2026; Fang2024].
2. **Context check before "tired".** Is the ball in play? What is the score? Is it the start of a half? Was the first-half load low? Was the player just substituted on? Did the team just lose or win the ball? If a non-fatigue reason fits, the agent says so or uses neutral words ("ran less") [Bradley2013; Morgans2025; Cortez2026].
3. **Compare phases per minute of that phase**, never as raw totals. Totals mostly reflect how long a team had the ball [Andrzejewski2022 vs Allen2026b].
4. **Block "they won because they ran more".** Winners outrun losers only slightly (total distance +0.7%, ES 0.22) [Allen2026a, Table 3]; total distance is unrelated to points (r = .04) [Allen2026b]; technical variables matter more [Andrzejewski2022].
5. **Never say "exhausted" or "empty" from the battery** (claim 19c) [Bellenger2025; Skiba2021].
6. **Never compare acceleration counts with published numbers.** They differ about 10-fold between tracking systems [Castellano2025, Table 3; Morgans2025b, Table 1].
7. Never link a misplaced pass, missed shot or bad decision to fatigue (claims 20–22) [Fang2024; Carling2011; Dambroz2022].
8. Estimate language only ("likely", "our estimate"); no claims about a player's physiology.

**Heart rate.** Not part of the core model. Estimating heart rate from speed adds a guess on top of a guess. If we want it for fans, we show a clearly labelled "estimated effort" based on [Bangsbo2006].

---

## 4. Architecture (first draft)

```
Simulator ──► Azure Event Hubs ──► Ingest ──► Fatigue engine ──► shared match state
 (Python)       (live stream)                  (Python)            (Cosmos DB / Redis)
                                                                        │
         ┌──────────────────────────────────────────────────────────────┤
         ▼                       ▼                        ▼              ▼
  Tactical agent          Narrator agent         Personalization    Verifier agent
  (finds moments where    (explains why, in      agent (fan vs.     (checks claims vs.
   fatigue mattered)       plain English)         analyst, fav.      data, blocks
                                                  player)            unsupported ones)
         └──────────────── Microsoft Foundry + Agent Framework ─────────┘
                                         │
                                         ▼
                       Web app: match replay + battery overlays
                       + live explanation feed (Azure Container Apps)
```

- The **fatigue engine is plain code**, not an LLM. The agents call it through tools (an MCP server), so every number they quote comes from the model.
- The **Verifier agent** checks every sentence against the data and the rulebook (section 3.4) before it reaches the screen. That covers both "explainable" and "responsible AI."
- The overlay output is **timestamped JSON**, so it can be synced to a video feed (the rules ask for this).

---

## 5. Timeline

Replaced by the day-by-day plan and cut list in [BUILD_PLAN.md](BUILD_PLAN.md). Two rules carry over: **submit early on October 27**, and **never cut the realism check or the fatigue validation chart**.

---

## 6. Open questions

- Do we have Foundry model access on the Azure free account ($200 credit)? Check model quota on day 1.
- Licences checked 2026-10-14: Sutcliffe2025 data CC0 (summary file only); daSilva2025 pitch-control code (github.com/Markfds01/Tracking_laliga) MIT.

---

Answered 2026-10-14: solo developer; Python for simulator, engine and agents; React + Vite + TypeScript for the front end; English only (no second language); no email to the organizers.

---

## 7. Decisions (settled 2026-10-14)

| # | Decision | Choice | Main source |
|---|---|---|---|
| 1 | CS and D′ source | Broadcast only: shared prior, updated per player from match data (decision 9). Club test values only as a validation experiment (revised 2026-10-15) | [Mizelman2024, p.2064]; synthesis §3.2.5 |
| 2 | Battery recharge | τ = k·D′/(CS − speed), k = 4; sensitivity k = 1, 3, 5; relative gauge only | [Bellenger2025; Skiba2021] |
| 3 | Settings by position | One shared prior; differences come from role behaviour | synthesis §3.2.3 |
| 4 | Position targets | 2024/25 targets in synthesis §4.2; counts from Castellano2025 | [Allen2024; Allen2025; Castellano2025] |
| 5 | Passing | No accuracy penalty; no ball-speed penalty in v1 | [Fang2024; Carling2011]; [Russell2011] lab only |
| 6 | Pitch control | Spearman/Shaw model as used by daSilva2025 | [Spearman2017; Spearman2018; daSilva2025] |
| 7 | Capacity check | Not built; optional post-match analyst view if time allows | [AlonsoCallejo2024; Morin2021] |
| 8 | Second truth model | Cut unless time allows | [Weigend2023] |
| 9 | Updating CS and D′ during a match (added 2026-10-15) | Light Bayesian update per player: ~200 draws from the prior, weighted by how well each fits the player's running; median battery with a 10–90% band. One-way D′ correction kept as fallback. k fixed per run | Section 3.2; synthesis §3.2.3, §3.2.5, §3.7; [Sutcliffe2025; Mizelman2024] |
| 10 | Skipped runs (added 2026-10-16) | The estimator does not try to detect skipped runs or intentions: real tracking shows only what players did. It scores tired moments (`tired`) and late-match wear (tank trend). The hidden skipped runs are used to check the generator against Ju2022 and to pick demo moments, worded as what happened ("ran back slower than usual"), never what the player meant to do. A positions-only "slow response" detector scored against them is a stretch goal | Section 3.3; [Ju2022] |
| 11 | Known generator gaps accepted (added 2026-10-16) | Team and full-back sprint distance 7–9% above target, recovery time between efforts +12% (pass +15 to +40), post-peak drop too steep even without fatigue, home/away total-distance r 0.96: documented, not tuned further before the estimator | Commits 6ca789f, 7c387c7, bc51565 |
| 12 | Tired moments (added 2026-10-16) | Tired = battery below 50% of the player's estimated D′, nothing else: precision about 0.3 from positions, so the agents say "likely tiring" sparingly and quote the measured precision. The post-peak flag is a separate signal with neutral words ("catching breath after a red-zone spell"), never "tired": adding it to the tired flag gave precision 0.13–0.16, and post-peak drops appear even with fatigue off (§2.5) | Section 3.3 "As built"; `engine/params.py` |
