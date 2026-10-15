# Second Wind: Project Plan

> The story the scoreline doesn't tell: who's running on empty, and when it costs them.

Citations like `[Leifsson2024]` refer to keys in [READING_LIST.md](READING_LIST.md). Page, table and figure references for every number are in [RESEARCH_SYNTHESIS.md](RESEARCH_SYNTHESIS.md), cited here as "synthesis §x".

**Deadline:** October 27, 2026, 11:59 pm Pacific Time.

**Updated 2026-10-14.** The research phase is finished (64 papers) and the open decisions are settled (section 7). The build plan is in [BUILD_PLAN.md](BUILD_PLAN.md).

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

**Story controls.** Seeded parameters to create interesting matches on demand: "Team A presses high for 60 min then fades," "the left-back is exposed by repeated counterattacks," "a fresh substitute makes the difference."

**Output format** (full schema in synthesis §7):
- `events.jsonl`: one event per line: id, time, period, type, subtype, player, team, start and end location, outcome, possession id, **phase** label, score state. Types include **carry** (start and end) and **reception**, so carry speed and receiving speed can be computed [Fang2024].
- `tracking.jsonl`: one frame per line (10 Hz): time, period, **ball in/out of play**, **team in possession**, ball x/y/z, and x/y for 22 players. Realistic position noise (σ ≈ 0.1 m plus dropouts, synthesis §3.1). Speeds are optional; the estimator recomputes them from positions.
- `metadata.json`: teams, line-ups, formations, positions (GK, CB, FB, DM, CM, AM, WM, CF, as in [Allen2024]), substitutions, fictional names and clubs. Per-player **club test values** (CS, D′, A0, S0) with ±5–10% error vs the truth, used only in club mode (section 3.2).
- `truth.json`: the hidden "true" fatigue per player per second: fast pool, slow pool, tank, capacity multipliers, the **intended purpose of each run**, skipped runs, and true tired-moment labels [Fang2024; Ju2022; Allen2026b]. **Only for validation, never given to the estimator.**

Follow an existing event schema (e.g. SPADL or StatsBomb-like) so it looks professional and other tools can read it.

### 2.4 Why the ground truth matters (our strongest rigour point)

Because we generate the data, we know the "true" fatigue. So we can **measure how good our estimator is**, something nobody can do with real matches, where fatigue is never measured directly.

To avoid a circular argument (testing the model against itself), the simulator's physiology is **different and richer** than the estimator's:
- **Truth:** two pools, a whole-match tank, individual parameters, and behaviour rules (section 2.3).
- **Estimator:** one D′ balance plus metabolic power, from positions only (section 3).

Stretch goal, **cut unless time allows**: a second, structurally different truth model (three-tank hydraulic [Weigend2023]) to show the estimator copes with model mismatch. Its equations are in Weigend 2021, which is not in our set, and fitting takes at least 3 h per CS/D′ pair [Weigend2023, §4.2].

### 2.5 Realism check

We compare synthetic matches against published numbers and open data, and show the comparison in the README. Pass thresholds are our proposals (synthesis §6.1).

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
| **No-fatigue control match** | See below | synthesis §6.2 |

**No-fatigue control match.** Picking each player's most intense window guarantees lower values afterwards, even with no fatigue at all. Play also stops after peaks: ball in play falls from 82% to 57% in the minute after a peak [Cortez2026, Table 3]. So:
1. Generate the same matches (same seeds and tactics) with fatigue **switched off**.
2. Run the exact Leifsson2024 and Ju2022 pipelines on both sets.
3. Show three curves side by side: published, synthetic with fatigue, synthetic without fatigue.
4. Calibrate so the with-fatigue curve matches Leifsson2024. The gap between the two synthetic curves is the part that is really fatigue.

No published study controls for this, so it is our strongest rigour slide.

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
| **Broadcast (default)** | One prior for all outfield players: CS 3.7 m/s (13.3 km/h), D′ 180 m [Sutcliffe2025, Fig. 2; Liu2021, Table 4; synthesis §3.2.3]. **One-way correction from match data:** if the battery would drop below zero, raise D′ to fit what the player actually did. Never lower D′ or move CS during a match. | Fans, TV, the league |
| **Club (analyst)** | Club test values from metadata (true value ±5–10%), plus the same correction | A club's own staff |

- Position differences come from role behaviour, not from different settings. No paper gives CS or D′ by position (synthesis §3.2.3).
- Validation runs both modes against the truth, to show how much accuracy is lost without test data.
- A full "prior plus match update" fit (synthesis §3.2.5, option C) is a stretch goal.

### 3.3 Signals

| Signal | Method | Source |
|---|---|---|
| **Battery (short-term)** | D′ balance: drains by (speed − CS) metres per second above CS. Below CS it recharges with recharge time τ = k·D′/(CS − speed), **k = 4**, clipped to 30–900 s. Sensitivity runs at k = 1, 3 and 5. With default settings, τ ≈ 195 s standing and ≈ 330 s walking (derived). **A relative gauge only**: "lowest point of his match", "lower than his teammates", never "empty" or "exhausted". | [Skiba2021; Jones2017, p.S76]. The standard form (k = 1) recharged about 5× too fast in runners: 68 s vs 362 s fitted [Bellenger2025, p.721–722, Figs 2–4] |
| **Load (whole match)** | Metabolic power from speed **and** acceleration. Report rolling 1- and 5-min averages and total energy; never "distance above 20 W/kg". | [Osgnach2010; diPrampero2005]; zone distance varies 73.6% between trials [Buchheit2015, Table 2] |
| **Recent intensity** | Rolling 1-, 2- and 5-min high-speed distance compared with the player's own peak curve. "Post-peak" flag for about 2 min after a 1–2-min peak and about 5 min after a 5-min peak. Rates per ball-in-play minute. Tracks high-speed running separately from total distance. | [Leifsson2024, Table 1; Thoseby2023, Table 2; Fang2024] |
| **Effect on play** | Pitch control, Spearman/Shaw model as used by da Silva: σ 0.45 s, λ 4.3 s⁻¹ [Spearman2017, p.7]; reaction time 0.7 s, goalkeeper λ 12.9 s⁻¹, ball speed 15 m/s (54 km/h) [daSilva2025, p.3]; κ = 1. Computed from **actual positions** at event moments (or 1–2 Hz), so a skipped recovery run shows up directly. A "fresh" version is shown only as a labelled model estimate. | [Spearman2018, Eq. 3–4; daSilva2025] |
| **Confidence** | Every number is an estimate with a band. Band width comes from our own validation against the truth; floor is the 7–20% typical error of D′ estimates. Fan mode shows a 5-level battery icon. | [Skiba2021, p.1567; Buchheit2015] |

**Not built: capacity check (acceleration–speed profile).** One match doesn't give a reliable profile: match-only A0 vs a sprint test ICC 0.23 [AlonsoCallejo2024, Table 2]. Its noise (A0 5.4% [Morin2021, Table 1]) is larger than the 2–4% loss we would be looking for [SilvaJR2018, Table 5; Krustrup2006, p.1171]. A0 and S0 stay as simulator limits and metadata values. If time is left over: a post-match, half-vs-half analyst view labelled "low confidence".

**Tired moment detection.** A defensive action (duel, recovery run, pressure) by a player whose battery is low **for them**, or who is inside a post-peak window. Losing the ball (negative transition) gives the hardest running of the game for total distance [Bortnik2022, Fig. 3; one Polish team, GPS], so it is the first place to look. The main pattern the agents explain: in the Premier League, after a peak spell, players do 22–44% less Covering and 34–43% less Recovery Running than their match average [Ju2022, p.975].

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
| 1 | CS and D′ source | Two modes: broadcast (shared prior + one-way D′ correction) and club (test values ±5–10%) | [Mizelman2024, p.2064]; synthesis §3.2.5 |
| 2 | Battery recharge | τ = k·D′/(CS − speed), k = 4; sensitivity k = 1, 3, 5; relative gauge only | [Bellenger2025; Skiba2021] |
| 3 | Settings by position | One shared prior; differences come from role behaviour | synthesis §3.2.3 |
| 4 | Position targets | 2024/25 targets in synthesis §4.2; counts from Castellano2025 | [Allen2024; Allen2025; Castellano2025] |
| 5 | Passing | No accuracy penalty; no ball-speed penalty in v1 | [Fang2024; Carling2011]; [Russell2011] lab only |
| 6 | Pitch control | Spearman/Shaw model as used by daSilva2025 | [Spearman2017; Spearman2018; daSilva2025] |
| 7 | Capacity check | Not built; optional post-match analyst view if time allows | [AlonsoCallejo2024; Morin2021] |
| 8 | Second truth model | Cut unless time allows | [Weigend2023] |
