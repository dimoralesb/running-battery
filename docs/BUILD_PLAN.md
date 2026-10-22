# Running Battery: Build Plan

**Status (2026-10-21):** decision 39, from the clip audit and the user's call to put the presentation first: team-mates no longer crowd each other in play (0.14% → 0.01% of player-frames within 1 m), keepers stay within 22.5 m of their line, restart takers and walls stand where they should, and midfield running is retuned (high-speed running per position within ±5% again); every realism and validation number re-run on 240 seeds and the match batches. The feed and the clips were reworked: a counter that ended in a goal says so, and the favourite's goal-ending turnover is always picked; a second wind says his running against his match average and a quiet spell why it may not be fatigue (the verified template steps in when the LLM's lines leave it out); fresh legs only for a substitute who out-ran his team-mates; no early flat-out moment below 95% of his top speed; his hardest minutes counted as times, not flickers of the flag ("for the eighth time" at 19:50 was mostly one stretch); one clip per action across players; a clip stays inside its half; a back-to-back or busiest-minute clip fast-forwards between his runs; G5 also reads a percentage of plain "running". Demo matches and feeds regenerated (site feed: 13 moments, 56 lines shown, 10 blocked; clip audit: 20 clips in each match, no player vanishing, 8 of 8 clear chances shot, no ball jumps); §6 updated to the new moments. Next: the video (§6) and the repository made public (§7), the user's call. **Earlier (2026-10-20, evening):** decision 38, from the user's review of the clips: players shoot on clear chances (13 of 23 had been backward passes), the ball rolls to the player who takes it (it jumped 4–7 m in 0.1 s 32 times a match), a player the tracking loses for a moment is drawn faded between his positions, each moment's clip shows the part of the match it is about (with a one-line explanation of the moment), one clip per action, and a substitute's clip numbers no longer read 0. Generator retuned on 60 seeds; every realism and validation number re-run on 240 seeds and the match batches; demo matches and feeds regenerated; three Verifier rules (G13 scorelines, G5 for players, G14) and "level" checked against the gap, each from a line on the site's feed; the clip audit is `scripts/clip_audit.py`. §6 updated to the new moments. Next: the video (§6) and the repository made public (§7), the user's call. **Earlier (2026-10-20, later):** decision 37: a clip plays with video controls (progress bar, time, ½× 1× 2×), Replay at normal speed, plainer titles ("High-speed running per minute", "High-speed running by situation", "Commentary") and the battery caption "Expected for a typical pro after the same running". The simulator's run rules are fixed (number 9 in clip 1 ran past the keeper, crowded team-mates and pressed a covered carrier), five run chances retuned, every realism and validation number re-run on the new generator, the demo matches and feeds regenerated (a tools bug behind a false "fastest of anyone" fixed on the way), and §6 updated to the new moments. Next: the video (§6) and the repository made public (§7), the user's call. **Earlier (2026-10-20):** renamed Running Battery (decision 35); the overlay redesigned as a cleaned-up broadcast (decision 36: JOURNEY.md, DESIGN.md, brief and mocks in `.design-foundations/`); §6 matches the new screen. Next: the video (§6) and the repository made public (§7), the user's call. **Before (2026-10-19):** approved and in progress, about seven days ahead. Done: Wed 14 to Tue 20, Wed 21 (MCP server, claims register, Verifier v1 and v2), Thu 22 (agents and the feed, on Foundry: decision 18), Fri 23 (overlay: replay, batteries, flat-out pulse, reachable-area circles labelled "model", traces, the team chart, the verified feed; light, dark and phone checked), Sat 24 (public site on Azure Static Web Apps, Free: decision 26), Sun 25 (README: data card, realism table with the † rows re-run, charts, Verifier table, what we don't claim). The feed holds to its prompts in code (decision 25); physical highlights (decision 28); the Highlights view as the default, football's words for our terms ("intense spell") and two more highlights (decision 29); "his hardest minutes" for that window and where each team's running happened, with pressing tested against the hidden truth and left out (decision 30); team names in full, "level", and the lines the video's moments need, with the site's feed regenerated (decision 31). The battery back in every view, with broadcast graphics (decision 32). Mon 26's pitch text ([PITCH.md](PITCH.md)) and clean-clone test are done (§7). The unused test Container App and its environment are deleted. Next (the user's call, 2026-10-19: more changes first): the video (§6) and making the repository public (§7). Science frozen (decision 17).
Deadline: October 27, 2026, 11:59 pm PT. Design and sources are in [PLAN.md](PLAN.md). Numbers and targets are in [RESEARCH_SYNTHESIS.md](RESEARCH_SYNTHESIS.md) ("synthesis §x").
Solo developer. Python 3.12 for everything except the front end (React + Vite + TypeScript). English only. Azure free account ($200 credit); Foundry access confirmed on October 17 (gpt-5-mini; PLAN decision 18).

## 1. Modules

| Module | What it does | Main inputs → outputs |
|---|---|---|
| **`sim/` Generator** | Phase state machine (ball status, possession, phases, events). Movement at 10 Hz (Narizuka motion model, A0/S0 limits). Role behaviours (covering, recovery runs, pressing), each run labelled with its purpose. Hidden physiology: two pools + tank, with a **fatigue on/off switch**. Shared team tempo. Position noise. | seed, story controls → the 4 files below |
| **`engine/` Estimator** | Butterworth 1 Hz + central differences. Metabolic power. Battery (k, broadcast mode with a per-player update of CS and D′ from the shared prior: ~200 draws, median + 10–90% band; one-way D′ correction as fallback; club test values only in a validation run; PLAN §7, decision 9). Rolling 1/2/5-min intensity and post-peak flags. Tired-moment detection. Pitch control at event moments. | tracking + events + metadata → per-player, per-second signals and moments (JSON) |
| **`validate/`** | Realism checks, the no-fatigue control, estimator vs truth, sensitivity runs, Verifier test suite. Writes charts and tables for the README. | batches of synthetic matches → report |
| **`agents/`** | MCP server over the engine. Four agents on Foundry + Agent Framework: Tactical, Narrator, Personalization, Verifier. The claims register (synthesis §5) is a data file; the Verifier runs fixed rule checks first, then the LLM. | engine signals → checked, sourced sentences |
| **`app/` Overlay** | Highlights view (each clip, then its details; Replay on request, decision 34) and the full-match replay: battery icons (fan) or traces with bands (analyst), explanation feed, favourite player. Timestamped JSON output for video sync. Azure Static Web Apps (decision 26). | exported match files → web UI |

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
4. ~~Pitch control~~ (2026-10-18: reachable-area circles instead [Narizuka2023], labelled "model"; removed 2026-10-20, decision 37: at 1 s their size is fixed, about 6.2 m, so they said little a first-time viewer could use).
5. Merge the Personalization agent into the Narrator.
6. ~~Club mode~~ (decided 2026-10-15: broadcast is the only product mode; club data stays as one validation run).
7. Shorter realism table: keep position totals, post-peak curves, end-of-match decline and running by phase.

## 6. Video plan (Mon 26, under 2 min)

Captured from the public site in the **Highlights view** (decision 29), one clip per shot: each
link opens a clip playing, or with `&step=details` stopped on its details (decision 34: no automatic
replay; `&step=replay` plays the replay with the details growing; since decision 37 at 1×, with a progress bar and ½× 1× 2×), so every shot
can be recorded again from its link. Story match, favourite H04 (the site's feed is
`docs/feeds/story_h04.json`). Voice-over in the register's words; every sentence on screen is the
feed's or a highlight caption, all checked by the Verifier. Since decision 36 the screen is a
cleaned-up broadcast: the brand line "Running Battery · synthetic match" with its tagline, the
score bug, the pitch, the lower third under it with the player's battery as it plays (the one
bold graphic), the play bar, then the tabs Clips, Team sheet, Details and Settings. Record at
1440×900: when a clip ends the Details tab opens under the pitch with the numbers and the first
line on screen; scroll the page for the rest of the lines (or shoot `&step=details` and scroll).
Since decision 39 the match is regenerated again (team-mates, keepers and restart takers kept
where they belong, midfield running retuned) and so are its moments: H04's recovery run is gone,
his caught-on-the-break clip that ends in a goal is in. A clip at 1× stays inside its half, and a
back-to-back or busiest-minute clip fast-forwards between his runs (the play bar says so).
Base URL: `https://happy-bay-06ca1e90f.3.azurestaticapps.net/?match=story`
(decision 35: the name, with its tagline, is on screen in every shot).

| Time | Shot (add to the base URL) | Says |
|---|---|---|
| 0:00–0:08 | The site opening on the Highlights view (no extra parameters) | The scoreline doesn't tell you who did the hard running, or what it cost. This match is synthetic, generated from published sports science. |
| 0:08–0:30 | Marco Tarvsall at 19:50, the lowest point of his match so far (lines: "…about 49% of their short-term reserve." and "This is the lowest point of his match so far, by our estimate."), the clip then its details (`&moment=red_zone:H04:1:1190`, or `&item=4`; then `&step=replay` for the replay with the numbers growing; pick ½× on the play bar for slow motion) | Marco Tarvsall, 19:50: 68 m of high-speed running in one minute, against a published average best minute of 62 m. It is the lowest point of his match by our estimate: running that would leave a typical professional at about 49% of their short-term reserve. Measured from positions: what he did, never how hard he tried. |
| 0:30–0:55 | H04 caught on the break at 30:11, the clip then its details (`&moment=exposed_on_turnover:H04:1:1811`, then `&step=details`). The clip runs from the turnover to the goal (15 s). Lines: "That running would leave a typical professional at about 72% of their short-term reserve, by our estimate." (claim 11), "This is the fourth time Marco Tarvsall's team have lost the ball just after his hardest minutes so far." and "The turnover sparked a 15 s counter that produced a goal."; analyst: "A 15 s counter-attack followed and it resulted in a goal (counter xG 0.12); the ball was nearest him at about 7 m." | His team lost the ball just after his hardest minutes, for the fourth time; he was 33 m from it, and 15 seconds later the counter was a goal. Five minutes earlier, at 25:42, his running would have left a typical professional at about 52%: about the running, never "he's tired". |
| 0:55–1:10 | The gap closing at 45+1:04 (`&moment=tug_of_war:home:1:2764&step=details`), with `&mode=analyst`: a line the rules blocked ("The gap has closed — the two sides were level in this block after a 32% gap earlier in the match.", G10: the teams were 2% apart) and the lines shown instead ("…163 m of high-speed running per ball-in-play minute in 30:00–45+1:05, 2% more than Ravensholt Albion's 160 m."); fan mode has the same block in its own words. Then "High-speed running by situation" below it | Every sentence is checked: fixed rules, then an LLM that can only block and writes down its fact check first (192 test sentences, README table). Westerlyn Albion did 32% more high-speed running per ball-in-play minute in the first 15 minutes, 2% more by half-time; in 30:00–45+1:05, 45% of their high-speed running came in the first 10 s after the ball changed hands, in 28% of the ball-in-play time (`match.json` `team_situations`). |
| 1:10–1:25 | Fresh legs at 69:52 (`&moment=fresh_legs:H16:2:1887`): his longest high-speed run in his first 10 minutes; line: "Since coming on, Felix Morrmere has done 16.0 m of high-speed running per minute, 70% more than his team-mates over the same minutes." Then the Clips tab's fastest player per team | The substitute who came on for him has done 70% more high-speed running per minute than his team-mates over the same minutes. |
| 1:25–1:45 | Estimator-vs-truth and no-fatigue charts (README) | Tested against the generator's hidden truth: what positions can and cannot tell, and what we therefore don't claim. |
| 1:45–1:55 | Architecture line: generator → estimator → MCP → four agents on Foundry → Static Web Apps; then "Full match" for two seconds | Microsoft Foundry, Agent Framework, MCP, Azure. Link. |

**Never cut:** the no-fatigue control, the estimator-vs-truth chart, the real-data conclusion check on IDSSE (PLAN §2.6), and the rule-based Verifier. If the LLM Verifier slips, the fixed rule checks still block unsupported claims.

## 7. Submission checklist (Tue 27, morning; OFFICIAL RULES §4.4)

Checked on 2026-10-19 unless marked open.

- [ ] **Repository public.** The rules: "Your repository must be public for your entry to be
  considered." It is private now; the user makes it public when the last changes are in
  (`gh repo edit dimoralesb/running-battery --visibility public --accept-visibility-change-consequences`).
  History checked: one author; no `.env`, keys, endpoint or subscription id, IDSSE data, papers
  or rules text in any commit (only our IDSSE loader scripts).
- [ ] **Project pitch** in the form: [PITCH.md](PITCH.md), short or full version. The rules set
  no length; check the form's own limit on the day. Every sentence passes the Verifier's rules
  (`tests/test_pitch.py`).
- [ ] **Video** under 2 min, public on YouTube or Vimeo, no third-party trademarks or
  copyrighted music (team and player names are generated); its URL on the project page. Open:
  recording and voice-over (§6).
- [x] **Working project for judges**: https://happy-bay-06ca1e90f.3.azurestaticapps.net/?match=story,
  no login, free until judging ends on 2026-11-10 (Static Web Apps Free plan, $0).
- [x] **Licence**: MIT ([LICENSE](../LICENSE)); third-party data (IDSSE, CC BY 4.0) is not
  redistributed.
- [x] **Clean clone** (of 87d02cd, 2026-10-19): README "Development" from a fresh clone, no `.env`: `uv sync`, 287 tests
  passed (1 skipped without IDSSE), ruff clean, `npm ci && npm run build`, the story match, an
  offline feed and the export.
- [x] **Azure credit**: about $11.73 used of $200 (Cost Management, 1–19 Oct: Foundry Models
  $10.64, Event Hubs $1.10 before it was deleted). The site costs nothing; Foundry is only used when
  feeds or the suite are regenerated. The Foundry resource and its resource group stay.
- [ ] **English**: all materials are in English.
- [ ] On the day: CI green on the submitted commit; the site serves `docs/feeds/story_h04.json`
  from that commit.
