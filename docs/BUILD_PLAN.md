# Second Wind: Build Plan

**Status (2026-10-18):** approved and in progress, about four days ahead. Done: Wed 14 to Tue 20, Wed 21 (MCP server, claims register, Verifier v1 and v2), Thu 22 (agents and the feed, on Foundry: decision 18), Fri 23 (overlay: replay, batteries for the selected, favourite and five lowest players, flat-out pulse, reachable-area circles labelled "model", traces, tug of war, the verified feed; light, dark and phone checked), Sat 24 (public site on Azure Static Web Apps, Free: decision 26) and most of Sun 25 (README: data card, realism table, charts, Verifier table, what we don't claim). The feed holds to its prompts in code (decision 25). Next: Mon 26 (video, clean-clone test). Science frozen (decision 17).
Deadline: October 27, 2026, 11:59 pm PT. Design and sources are in [PLAN.md](PLAN.md). Numbers and targets are in [RESEARCH_SYNTHESIS.md](RESEARCH_SYNTHESIS.md) ("synthesis §x").
Solo developer. Python 3.12 for everything except the front end (React + Vite + TypeScript). English only. Azure free account ($200 credit); Foundry access confirmed on October 17 (gpt-5-mini; PLAN decision 18).

## 1. Modules

| Module | What it does | Main inputs → outputs |
|---|---|---|
| **`sim/` Generator** | Phase state machine (ball status, possession, phases, events). Movement at 10 Hz (Narizuka motion model, A0/S0 limits). Role behaviours (covering, recovery runs, pressing), each run labelled with its purpose. Hidden physiology: two pools + tank, with a **fatigue on/off switch**. Shared team tempo. Position noise. | seed, story controls → the 4 files below |
| **`engine/` Estimator** | Butterworth 1 Hz + central differences. Metabolic power. Battery (k, broadcast mode with a per-player update of CS and D′ from the shared prior: ~200 draws, median + 10–90% band; one-way D′ correction as fallback; club test values only in a validation run; PLAN §7, decision 9). Rolling 1/2/5-min intensity and post-peak flags. Tired-moment detection. Pitch control at event moments. | tracking + events + metadata → per-player, per-second signals and moments (JSON) |
| **`validate/`** | Realism checks, the no-fatigue control, estimator vs truth, sensitivity runs, Verifier test suite. Writes charts and tables for the README. | batches of synthetic matches → report |
| **`agents/`** | MCP server over the engine. Four agents on Foundry + Agent Framework: Tactical, Narrator, Personalization, Verifier. The claims register (synthesis §5) is a data file; the Verifier runs fixed rule checks first, then the LLM. | engine signals → checked, sourced sentences |
| **`app/` Overlay** | Pitch replay, battery icons (fan) or traces with bands (analyst), story cards, explanation feed, favourite player. Timestamped JSON output for video sync. Azure Container Apps; Event Hubs for the live stream. | shared match state → web UI |

## 2. Data schema (synthesis §7; PLAN §2.3)

- **`tracking.jsonl`** (10 Hz): `frame, t, period, clock, ball_status, possession_team, ball{x,y,z}, players[{id,x,y}]`. Centre origin, metres, 105 × 68 m pitch. White noise σ = 0.05 m per axis plus dropouts (`sim/params.py`, `NOISE_SIGMA`).
- **`events.jsonl`**: `id, t, period, type, subtype, player_id, team_id, start_xy, end_xy, outcome, body_part, possession_id, phase, score_state`. Types include pass, **carry**, **reception**, shot (xG), duel, tackle, interception, pressure, recovery, loss, fouls, restarts, substitutions, goals and cards.
- **`metadata.json`**: teams, line-ups, formations, positions (GK/CB/FB/DM/CM/AM/WM/CF), substitutions. Club test values (CS, D′, A0, S0 = truth plus measurement error) only with `--club-tests`, for the club-data experiment.
- **`truth.json`** (1 Hz, validation only): fast pool, slow pool, tank, capacity multipliers, the purpose of each run, skipped runs, tired-moment labels.
- A JSON Schema for each file is written first; the generator, estimator and app are all checked against it.

## 3. Validation runs (synthesis §6)

1. **Realism** (PLAN §2.5 table): 50 matches with fatigue on. Movement checks first (distance, sprints, speed and acceleration distributions vs IDSSE); event counts are secondary (PLAN §2.6). Check position and team totals, match length, sprint counts, the two-team correlation, running by phase, ball in play, IDSSE speed and acceleration distributions, events, post-peak curves, peak timing and end-of-match decline.
2. **No-fatigue control:** the same 50 seeds with fatigue off. Run the Leifsson and Ju pipelines on both sets and plot published / with fatigue / without fatigue.
3. **Estimator vs truth:** correlation, mean absolute error and bias of battery %, 80% band coverage, and tired-moment precision ≥ 0.7 at recall ≥ 0.5 (our target, synthesis §6.3). The 50-match batch randomises its own assumptions (fatigue effect sizes, pool settings beyond the estimator's priors, noise, tempo) and results are reported across that spread. Tired-moment metrics use natural matches only, not story matches (PLAN §2.6).
4. **Real-data conclusion check:** run the estimator on the 7 IDSSE matches and compare conclusions with the synthetic batch: post-peak drops, second-half decline, battery-drop and tired-moment distributions (PLAN §2.6).
5. **Sensitivity runs:** k = 1, 3, 4, 5. Broadcast vs with club test values. Position noise σ = 0.05, 0.1, 0.3 and 1.0 m. Test values ±10%.
6. **Confounder cases**, where the agents must not say "tired": a 3–0 lead with the team sitting back, a long stoppage, the start of the 2nd half, and a low-load player's late drop.
7. **Verifier suite:** about 50 sentences, half valid and half from the blocked list. Every blocked sentence and every unbaselined % must be caught; report the false-block rate.

## 4. Day by day

| Day | Work | Done when |
|---|---|---|
| **Wed 14** | Repo, environment, JSON Schemas, CI (lint + tests). IDSSE via floodlight. Azure account created. | Schemas pass on a dummy file; IDSSE loads |
| **Thu 15** | Generator: phases, ball status, possession, events, 99.5-min match length, simple movement | One match writes all 4 files |
| **Fri 16** | Movement model, role behaviours with run purposes, noise. **Azure test deployment (~1 h):** empty Container App + Event Hub (Basic), to catch free-trial limits early | Replay plot looks like football; test app URL responds |
| **Sat 17** | Hidden physiology, fatigue switch, shared tempo, `truth.json` | Fatigue on/off changes behaviour |
| **Sun 18** | Realism checks v1 + calibration (50-match batch, randomised assumptions). Movement vs IDSSE first | Position totals within ±5%; speed/accel distributions vs IDSSE |
| **Mon 19** | Estimator: all signals, both modes, tired moments | Signals for one match |
| **Tue 20** | No-fatigue control, estimator vs truth, k and mode sensitivity. Real-data conclusion check on IDSSE (~½ day) | **The two "never cut" charts exist**; IDSSE vs synthetic comparison table |
| **Wed 21** | MCP server; claims register as a data file; rule-based Verifier + test suite | Verifier suite passes |
| **Thu 22** | Agents on Foundry (4 roles, handoffs, retry on failure) | Full match → explained timeline |
| **Fri 23** | Web app: replay, battery, feed, fan/analyst toggle, pitch control at events | Runs locally end to end |
| **Sat 24** | Azure: ~~Container Apps, Event Hubs live stream, shared state~~ Static Web Apps (Free) with the committed demo data (PLAN decision 26) | Public URL works |
| **Sun 25** | README (realism table, validation charts, synthetic-data card, citations); fix bugs | README complete |
| **Mon 26** | Video under 2 min, pitch text, final test from a clean clone | Video uploaded |
| **Tue 27** | **Submit in the morning** | Submitted |

Buffer: Sunday 25 and Monday 26 each have about half a day of slack.

## 5. If time runs short, cut in this order

1. Already cut: the second truth model, and the capacity check (A–S profile).
2. ~~Extra languages~~ (cut 2026-10-14: English only).
3. ~~Event Hubs~~ (cut 2026-10-18, PLAN decision 26: replay from files; the test namespace is deleted).
4. ~~Pitch control~~ (2026-10-18: reachable-area circles instead [Narizuka2023], labelled "model").
5. Merge the Personalization agent into the Narrator.
6. ~~Club mode~~ (decided 2026-10-15: broadcast is the only product mode; club data stays as one validation run).
7. Shorter realism table: keep position totals, post-peak curves, end-of-match decline and running by phase.

**Never cut:** the no-fatigue control, the estimator-vs-truth chart, the real-data conclusion check on IDSSE (PLAN §2.6), and the rule-based Verifier. If the LLM Verifier slips, the fixed rule checks still block unsupported claims.
