# Running Battery: technical notes

The detail behind the [README](../README.md): how the battery and the agents work, every test we
ran and its numbers, the synthetic data, and how to run each part. Citation keys such as
[Leifsson2024, Table 1] are entries in [References.bib](References.bib).

- [The battery](#the-battery)
- [The agents](#the-agents)
- [The check](#the-check)
- [What we tested and don't claim](#what-we-tested-and-dont-claim)
- [Validation](#validation)
- [Synthetic-data card](#synthetic-data-card)
- [The page](#the-page)
- [Limitations](#limitations)
- [Development](#development)

## The battery

The battery is a D′ balance [Skiba2012; Skiba2021; Jones2017] driven by speed. Above critical
speed (CS) it loses v − CS metres each second. Below it, it refills towards D′ with recharge time
τ = k·D′ / (CS − v), clipped to 30–900 s. The standard form (k = 1) refilled about five times too
fast in runners, 68 s against 362 s fitted [Bellenger2025, Figs 2–4], so we use k = 4. The battery
refills standing still over half-time, at most 15 minutes [IFAB2025, Law 7].

**Wear.** The refill slows as metres above CS build up over the match: τ × (1 + α(1 − e^(−W/s))),
with W the metres above CS so far (half of them cleared at half-time), α = 1.0 and s = 400 m. Both
were fitted on simulated matches 1–60 (a grid of 12; the lowest error within 0.001 with the bias
nearest zero). The idea follows the slower recovery after repeated efforts [Chorley2022]. Against
the simulator's hidden state, without wear → with wear:

| | Matches 1–60 (fitted) | Held out, 61–120 | Wider spread of players, 50 matches |
|---|---|---|---|
| Mean absolute error | 0.063 → 0.058 | 0.063 → 0.059 | 0.098 → 0.093 |
| Bias | +0.036 → −0.002 | +0.032 → −0.007 | +0.063 → +0.025 |
| 10–90% range holds the truth | 67% → 79% | 68% → 78% | 50% → 60% |

It finds the truly low moments no better (best precision at recall 0.1: 0.16 → 0.15). The simulator
has a similar mechanism, so part of the gain is the test bench agreeing with itself. On the 7 real
Bundesliga matches [Bassek2025] the battery dips deeper with wear: the median lowest battery per
player goes from 70% to 66%, and 5% of players go below half (none before), against 79 ± 6%
published for university players [Sutcliffe2025, Fig. 3].

**The typical professional.** Each player gets 200 draws of CS and D′. CS is 4.1 ± 0.3 m/s
(14.8 km/h), clipped to 3.5–4.7: critical speed sits at 70–90% of VO₂max [Jones2017, p.S67], and
we take about 85% of professionals' VO₂max [Modric2020, Table 1]. VO₂max doesn't differ between
outfield positions [Slimani2019; Modric2020], so one prior covers all of them. D′ is 180 ± 54 m,
clipped to 100–300, from university players [Sutcliffe2025, Fig. 2]: no professional D′ has been
published. CS can't be fitted from tracking: the same kind of match data gives 1.7 m/s
[Roecker2017, Table 4], 2.0 m/s [Mizelman2024, Table 3] or 3.6–4.0 m/s [Lord2020, Table 2]
depending on the model, and the authors of the 2.0 m/s fit call it "likely well below" true CS
[Mizelman2024, p.2064]. The 3.6–4.0 m/s fit is above the same players' best 5- and 10-minute mean
speeds (2.1–2.6 m/s), so it is not a speed they could hold.

A draw whose balance would go below zero is contradicted by the running. Its D′ is raised just
enough, and its weight falls as exp(−½ (raise / (0.1 · D′))²). The page shows the weighted middle
draw, and analysts also see the 10–90% range. The chance of falling below half of D′ is the
weighted share of draws below half, mapped by an isotonic fit on matches 1–60 (expected
calibration error on held-out matches 0.022 → 0.001).

**Running measures.** Speed comes from the positions through a 4th-order Butterworth low-pass
filter at 1 Hz. High-speed running is distance above 5.5 m/s (19.8 km/h) [Ju2022; Leifsson2024].
"His hardest minutes" is a rolling 1-, 2- or 5-minute window whose high-speed distance reaches 90%
of his own best window so far and at least 90% of the published average peak (62, 38 and 22 m/min
[Leifsson2024, Table 1]). After a 5-minute peak, high-speed running is back within 8% of the match
average by the fourth minute [Leifsson2024, Table 1].

An acceleration-based battery (metabolic power over the cost of steady running on grass
[diPrampero2005; Osgnach2010]) was tested and not used. With speed-based CS and D′ it empties every
real player (median lowest battery 5%), and a critical metabolic power has no published
professional value.

## The agents

Four agents on Microsoft Foundry (Agent Framework, gpt-5-mini) turn a match into a timestamped
feed (`feed.json`, synced to the replay or a video by `video_s`). They see the match only through
an MCP server with seven read-only tools (`match_summary`, `player_signals`, `find_moments`,
`team_running`, `moment_context`, `claim`, `verify`). Every number comes back with its unit and the
field it came from, and nothing in `agents/` can read the simulator's hidden state.

The first agent picks the moments: a player's hardest minutes, a defender caught on the break,
fresh legs after a substitution, flat-out runs near a player's top speed, and how the two teams'
running compares. The second writes from the findings list ([claims.json](../src/runningbattery/agents/claims.json):
46 statements, each with its sources, and marked supported, qualified or blocked). The third sets
the fan or analyst style. The fourth is the check.

Plain code holds the agents to what the prompts ask. Each moment offers only the findings that fit
it (the figure for after a player's hardest five minutes only after a stretch that long, "top speed
hardly drops" only after the 75th minute). A team moment always says how the two teams compare and
where each team's high-speed running happened. Each general finding is shown at most twice per
feed. The best moment of each kind is always in the feed, whatever the first agent picked, and so
is a turnover that cost a goal. There is no favourite player.

## The check

Fixed rules run first, then an AI pass that can block a sentence but not rewrite it. The rules
check every number against the moment's measurements and every general statement against the
findings list, and they read the moment's context: a sentence that blames fatigue while the team is
3–0 up, the ball is out of play or the player has just come on must say so. The check compares
statements with the list; it never reads the papers.

The test suite ([verifier_report.json](verifier_report.json)) has 192 sentences. The paraphrases are
blocked findings in other words, and the fact checks are sentences that do or do not agree with
their measurements. Both were written before the rules or the prompt that could catch them, and
never used to tune them.

| | Unsupported sentences blocked | Correct sentences blocked |
|---|---|---|
| Fixed rules | 87 of 119 (paraphrases 2 of 23, fact checks 0 of 6) | 0 of 73 |
| Fixed rules + AI | 116 of 119 (paraphrases 23 of 23, fact checks 4 of 6) | 1 of 73 |

The AI pass varies. Over ten runs, as the suite grew from 174 to 192 sentences, it blocked 95–98% of
the unsupported sentences and 0–7% of the correct ones. It still misses sentences that mislead
without a wrong number, such as "his fastest run so far" when it was not. The rules give the same
verdict every time and have never blocked a correct sentence in the suite. Most rules came from
reading the feeds: a scoreline has to be the score at that moment, "level" means no difference,
a share of a team's running has to give the share of the time too, and "pressing" is blocked
because positions can't show it. Every piece of text on the page ([copy.json](../app/src/copy.json))
passes the rules too.

## What we tested and don't claim

Each of these is a sentence fans would like to read. We tested it against the hidden state of the
simulated matches, it does not hold up from positions, and the check blocks it.

- "He is tired." With each player's true fitness, the simulator's own physiology finds the tired
  moments almost perfectly (precision 0.997). Without it, the best positions-only detector reaches
  a precision of 0.20 at recall 0.1, and our battery 0.15 (matches 1–60,
  [validate/ceiling.py](../src/runningbattery/validate/ceiling.py)). So we say what the running
  would cost a typical professional.
- "Which team is more tired." Home-minus-away differences pick the team with more short-term
  fatigue 42–57% of the time (chance is 50%), and the team with more late-match wear 32–70% of the
  time; more than one match in four is still wrong (60 matches,
  [validate/teams.py](../src/runningbattery/validate/teams.py)). We show each team's measured
  running per ball-in-play minute instead.
- "He ran slower than he could when it mattered." After his team lost the ball, a slow defender
  had no run asked of him by his role in 94% of cases and skipped one in 4.4%. Speed doesn't tell a
  skipped run from no run asked (AUC 0.37). We give the speed, its share of his top speed and what
  happened.
- "He misplaced that pass because he was tired." Pass completion is the same before and after a
  peak (80.3% against 80.5% [Fang2024, Fig. 1]) and across the match [Carling2011, Table I], so the
  simulator has no passing penalty and the check blocks the claim.
- "Albion pressed high." A positions-only rule built on a published definition of closing down
  [Ju2022, Table 1] matches the simulator's hidden close-down runs with precision 0.56 (base rate
  0.18) and recall 0.14 (73,863 runs, thresholds fixed before the first run,
  [validate/purposes.py](../src/runningbattery/validate/purposes.py)). The page shows where the
  running happened instead.
- "They won because they ran more." Winners outrun losers only slightly (total distance +0.7%
  [Allen2026a, Table 3]), and total distance is unrelated to points [Allen2026b].

## Validation

The battery (blue, with its range) against the simulator's hidden state (orange) for one player of
a validation match, the calibration of the chance before and after its map, and how well anything
could tell who is tired from positions alone:

![Estimator against the hidden truth](figures/estimator_vs_truth.png)

**No-fatigue control.** The same 240 simulated matches with fatigue switched on and off. Most of
the published drop after a player's most intense spell appears even without fatigue: picking the
peak guarantees a lower value next, and play stops after peaks [Cortez2026, Table 3]. The decline at
the end of the match is all fatigue.

![No-fatigue control](figures/no_fatigue_control.png)

**Realism.** 240 simulated matches (seeds 1–240) with fatigue on, and the same matches with fatigue
off in brackets, against published numbers. The pass bands are ours. The simulator's settings were
fitted by an algorithm (the method of simulated moments with a response surface and trust-region
steps, `sim.calibrate`) on seeds never used for this table.

| Check | Published (source) | Simulated (no fatigue) | |
|---|---|---|---|
| Running above 4 m/s, last 15 min against first 15 | −21% [Bradley2009, Fig. 2]; pass −10 to −30% | −27.2% (−8.6%) | pass |
| High-speed and sprint running, 2nd half against 1st | about level [Bradley2009, p.162]; pass ±10% | −13.3 / −12.4% (−6.6 / −6.5%) | below (real Bundesliga matches: −21%) |
| Recovery time between hard efforts, last 15 min against first 15 | +28% [Bradley2009, p.162–163]; pass +15 to +40% | +27.6% (+6.4%) | pass |
| 2nd half against 1st, by first-half load (high / moderate / low) | −12 / 0 / 0% [Bradley2013, p.4] | −18 / −12 / −7% (−11 / −4 / −1%) | deeper than published |
| Substitutes against whole-match players, same minutes | +15% [Bradley2013, Table IV] | +28% (+12%) | above |
| High-speed running after a 5-min peak, minutes 1–5, against match average | −45 −29 −13 −8 −4% [Leifsson2024, Table 1] | −68 −35 −13 −7 −2% (−61 −27 −17 −2 +2%) | minute 1 too deep, even without fatigue |
| 1-min high-speed peak | 62 m/min [Leifsson2024, Table 1] | 66 m/min (69) | close |
| Covering and recovery runs in the 5 min after a peak, against match average | −22 to −44% and −34 to −43% [Ju2022, p.975] | −35 / −35% (−27 / −26%) | both in range |
| Hard runs after a peak: length, duration, speed | −23%, −32%, −3% [Fang2024, Table 2] | −21%, −19%, −3% (−20%, −18%, −2%) | shorter, not enough |
| Distance, high-speed and sprint running per position | 2024/25 Premier League ±5% [Allen2024, Table 4; Allen2025] | distance within ±5% (keepers +8.6%); high-speed running CF +2.3, FB −2.7, CM −3.5, CB −3.6, AM −5.8, WM −8.7, DM −12.8%; sprint distance DM −0.1, FB −2.9, CF −3.4, AM −9.3, WM −9.6, CB −14.6, CM +17.3% | gaps listed below |
| Shots and goals per match | 23.4 shots and 2.6 goals in the Premier League [Pappalardo2019]; shots pass ±15% | 23.1 shots; 3.2 goals | shots pass; goals above |
| Time in speed bands against real tracking | ±3 points [Bassek2025; Osgnach2010] | within 1.9 points | pass |
| Ball in play | 50–63% [Kavanagh2024, p.80; Allen2026b, Table 2] | 59.0% | pass |
| Running by phase, per player | 133 / 145 / 63 m/min with the ball / without / stopped [Allen2026b, Table 5] | 129 / 141 / 59 | pass (±10%) |
| Home and away teams move together | r = 0.68–0.75 [Allen2026a, Fig. 2]; pass 0.5–0.85 | high-speed 0.79, high-intensity 0.80, sprint 0.67; total distance 0.96 | total distance above |
| Energy per player and match | 61.1 ± 6.6 kJ/kg [Osgnach2010, p.174] | 59.3 ± 4.9 kJ/kg; real Bundesliga 57.6 ± 4.5 | close |

Gaps we accepted: high-speed running of holding, wide and attacking midfielders; sprint distance of
centre-backs, central, attacking and wide midfielders; the second half's drop; keepers; the first
minute after a peak; substitutes; goals and corners; and how closely the two teams' total distance
moves together.

**Real matches.** The same code ran on every real match we could get: 7 Bundesliga matches from the
IDSSE dataset [Bassek2025] (TRACAB tracking, CC BY 4.0), 20 A-League 2024/25 matches from
SkillCorner Open Data (broadcast tracking, MIT), Metrica Sports' 2 sample matches, and Wyscout's
380 Premier League 2017/18 matches (events only [Pappalardo2019]). They were converted on our
machine; no real data, raw or derived, is in this repository or on the site. The real range is the
10th–90th percentile of the real matches. Per 90 player-minutes of outfield players unless marked:

| | IDSSE (7) | SkillCorner (20) | Metrica (2) | Real range | Simulated (30) |
|---|---|---|---|---|---|
| High-speed runs (above 5.5 m/s) | 49.7 | 59.4 | 39.1 | 43–71 | 55.9 |
| Runs lasting 1–2 s | 61% | 61% | 59% | 58–63% | **71%** |
| Runs of 5 s or more | 5.8 | 7.2 | 5.8 | | **2.5** |
| Runs starting within 20 s of the last | 9.2 | 10.6 | 6.4 | 6.8–14.5 | 12.9 |
| Turn-backs (a run within 10 s heading the other way) | 2.1 | 2.4 | 1.4 | 1.4–3.2 | 2.3 |
| Runs of 15 m or more ending within 2.5 m of a team-mate, per in-play hour | 1.14 | 1.24 | 0.74 | 0.8–1.8 | 1.41 |
| High-speed runs ending over 3 m offside | 0.2% | 0.2% | | 0–0.8% | 0.5% |
| Share of high-speed running without the ball done within 10 m of it | 51% | 47% | | 44.5–54% | **43.8%** |
| Ball in play | 55% | 54% | | 49–60% | 59% |
| Stoppages over 60 s per match | 6.3 | 8.0 | | 3–11 | 5.6 |
| Gap between the teams per 15-min block: median; 90th percentile | 9.6%; 22% | 14.5%; 31% | 7.1%; 24% | 7–24%; 17–42% | 11.6%; 27% |
| Hardest-minutes moments | 2.78 | | | | 2.85 |
| Back-to-back bouts | 1.18 | | | | 2.28 |

On the IDSSE matches the estimator reaches the same conclusions as on simulated ones: load,
distance per player, the battery's dips, the deep first minute after a 5-minute peak and the peaks
themselves (1-minute peak 65 against 65 m/min). The one difference: real players faded more in the
second half (high-speed running −21% against our −14%).

Events per match against Wyscout's Premier League (mean, 10th–90th percentile) [Pappalardo2019]:
shots 23.4 (17–30), ours 22.9; goals 2.6 (1–5), ours 2.9; corners 10.3 (6–15), ours **5.3**;
offsides 4.1 (1–7), ours 3.3; fouls 21.4 (15–28), ours 24.4; throw-ins 44.9 (33–58), ours 34.7;
passes 865 (715–1019), ours **711**.

## Synthetic-data card

One paragraph per item of the checklist in [RuizPinto2026, Table 3].

**Objective.** The data exists to test an estimator of how much hard running players have done and
what it would cost a typical professional, against a fatigue state that real matches never reveal.
It is not meant to stand in for real matches in any other analysis.

**Structure.** Four files per match: 10 Hz tracking of 22 players and the ball (positions in
metres, ball in or out of play, possession), events (passes, carries, receptions, shots with xG,
duels, substitutions and more, each with a phase of play), metadata (line-ups, positions,
substitutions) and, for validation only, the hidden state (two short-term pools and a whole-match
tank per player per second, the purpose of each run and the runs a tired player skipped). Story
matches hold more tired moments than natural ones on purpose [RuizPinto2026]; they are only used for
the demo, and precision and recall come from natural matches. Schemas are in
[schemas/](../schemas/).

**Generation.** A phase-of-play state machine, a sprint motion model [Narizuka2023] limited by each
player's acceleration–speed profile [Morin2021, Table 1], role behaviours (covering, recovery runs,
pressing), position noise of 0.05 m, and a hidden physiology from published studies
[Chorley2023; Bradley2009; Fang2024; Ju2022]. Players are drawn from the typical professional
population above. Effect sizes we could not find in the literature are labelled "our assumption"
in [sim/params.py](../src/runningbattery/sim/params.py). Every match regenerates from its seed.

**Constraints.** Fatigue changes which hard runs players make and how long and fast they are. It
doesn't change passing accuracy, decisions or shooting, because the studies find no such effect in
matches [Fang2024; Carling2011]. Top speed and acceleration fall by at most 5% [Bradley2009, p.163;
SilvaJR2018, Table 5]. Players don't pace themselves, so the late-match fade is all physiology; in
real matches part of it is the player's choice [Snyder2023].

**Utility and fidelity.** See the realism tables above. A no-fatigue control separates what is
fatigue from what is selection. On real matches the estimator reaches the same conclusions except
for the size of the second-half fade.

**Risk and deployment.** This shows that the estimator recovers fatigue under the published effects
we built in; it doesn't prove those effects in a given league. A model tuned only on this data would
learn our assumptions. So the product claims only what survives that limit (the running, and what
it would cost a typical professional), the check blocks the rest, and every screen says the match
is synthetic.

## The page

The page ([app/](../app/), React and TypeScript, built with Vite) opens on the highlights: a card
for each clip in match order, the clip on the pitch with only that player's path drawn, and beside
it the Details tab (the numbers, the commentary and the run's speed second by second). Clicking a
card, Play or Next never moves the page. Under the clip, "The whole match" gives both teams'
high-speed running per ball-in-play minute in 15-minute blocks, and split by situation: the first
10 s after losing the ball, the first 10 s after winning it [Bortnik2022, Table 2], settled on the
ball, and without it. Full match is the whole replay; How it works explains the battery, the agents
and the research.

The highlights are measured from positions: top speed (against the average match top speed for his
position [SilvaH2025, Table 1]), the longest run above 5.5 m/s (a typical high-speed run is about
19 m [Fang2024, Table 2; DiSalvo2007]), the recovery run (the longest high-speed run back towards
his own goal within 10 s of his team losing the ball), back-to-back runs (three or more with 20 s or
less between them; Premier League players usually get 51–101 s [Bradley2009, Table I]), the busiest
minute (against a published average best minute of 62 m [Leifsson2024, Table 1]) and the most
ground covered (against the Premier League average by position [Kavanagh2024, Table 2]). Hardest
accelerations and stops are left out: tracking systems count them about 10-fold apart.

Some clips were hidden by hand because their movement didn't look like football
([app/public/data/](../app/public/data/)`<match>/hidden.json`); their lines stay in the full match's
commentary. The two demo feeds, with every verdict including blocked lines, are in
[feeds/](feeds/).

## Limitations

- The simulated players don't pace themselves, so the simulator's late-match fade is all
  physiology; in real matches part of it is the player's choice [Snyder2023].
- The chance of falling below half is calibrated for typical professionals. On matches with a wider
  range of players it is poorly calibrated (expected calibration error 0.052 raw, 0.058 after the
  map), because a typical-pro signal can't see who is less fit.
- Real players faded more in the second half than ours (high-speed running −21% against −14%).
- The movement still differs from real football: runs are too short (71% last 1–2 s against
  59–61%, and runs of 5 s or more come 2.5 per 90 player-minutes against 5.8–7.2), players press
  near the ball a little less than real (43.8% against 44.5–54%), back-to-back runs come about
  twice as often as in the IDSSE matches, and a match has fewer corners (5.3 against 10.3), more
  goals (3.2 against 2.6) and slightly fewer passes (711 against 715–1019).
- 13 of the 33 clips in the two demo matches were hidden by hand. The simulator wasn't changed, so
  the full match still has that movement.
- The story match's high press is our setting; a scripted search keeps its biggest 15-minute gap
  between the teams at 28%, inside the real range. The natural match has no settings of ours.
- The AI part of the check varies from run to run, and the feed's wording with it. The committed
  demo feeds are one run each.
- The live runner reads a match file frame by frame without looking ahead. It isn't connected to a
  tracking provider's feed or a broadcaster's graphics, and the commentary is written per match,
  not per moment as it arrives.
- The same seed gives a slightly different match on another machine (floating point), so the page
  ships the exported demo data in `app/public/data/` rather than regenerating it.

## Development

Python 3.12 with [uv](https://docs.astral.sh/uv/), Node 20 or later.

```bash
uv sync --all-extras                 # Python environment
uv run pytest                        # tests (one skips without the IDSSE data)
uv run ruff check . && uv run ruff format --check .
uv run python -m runningbattery.schema   # re-export the JSON Schemas after changing the models
```

The demo pipeline, from a match to the page:

```bash
D=data/synthetic/demo/story
uv run python -m runningbattery.sim --seed 2028 --story press-fade --out $D   # the story match
uv run python -m runningbattery.engine $D                                     # signals.json
uv run --extra agents python -m runningbattery.agents.feed $D --offline --out $D/feed.json
uv run python -m runningbattery.export $D --out app/public/data/story --feed $D/feed.json
uv run python -m runningbattery.live $D --check    # the same match frame by frame, as if live
cd app && npm ci && npm run dev                    # http://localhost:5173/?match=story
```

`--offline` uses template lines and the rules-only check. The export overwrites the committed demo
data in `app/public/data/story` with this machine's match (`git checkout app/public/data` restores
it).

Simulator:

```bash
uv run python -m runningbattery.sim --seed 1 --out data/synthetic/m0001        # one match
uv run python -m runningbattery.sim.summary data/synthetic/m0001               # summarise it
uv run python -m runningbattery.sim.replay data/synthetic/m0001 --start 12:00  # replay.html
uv run python -m runningbattery.sim.batch --seeds 1-30 --json report.json      # means over 30 matches
uv run python -m runningbattery.sim.calibrate --rounds 3 --json out.json       # refit the settings
```

Estimator and validation:

```bash
uv run python -m runningbattery.validate.batch data/synthetic/validation    # estimator against the hidden state
uv run python -m runningbattery.validate.calibrate data/synthetic/dev       # refit the chance map
uv run python -m runningbattery.validate.real data/synthetic/dev --jobs 4   # IDSSE against simulated
uv run python -m runningbattery.validate.figures                            # docs/figures/*.png
```

The IDSSE data is for calibration only and never enters the repository: `uv sync --extra calib`,
`uv run python scripts/fetch_idsse.py` (about 2.4 GB), then `uv run python -m runningbattery.sim.idsse`
once.

Agents (`uv sync --extra agents`; Foundry settings in `.env` from `.env.example`, sign-in with
`az login`):

```bash
uv run python scripts/foundry_smoke.py                                       # model access and latency
uv run python -m runningbattery.agents.mcp_server data/synthetic/demo/story  # MCP server (stdio)
uv run python -m runningbattery.agents.feed data/synthetic/demo/story        # feed.json
uv run python -m runningbattery.agents.verifier_suite --llm --json docs/verifier_report.json
uv run python scripts/clip_audit.py data/synthetic/demo/story app/public/data/story
```

The page and its deployment (Azure Static Web Apps, Free plan):

```bash
cd app && npm ci && npm run dev    # http://localhost:5173/?match=story&mode=analyst
scripts/deploy_site.sh             # build app/ and deploy the committed data
```
