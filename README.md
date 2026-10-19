# Second Wind

> The story the scoreline doesn't tell: who has done the most hard running, and when it costs them.

Second Wind measures from tracking data how much hard running each football player has done and what it would cost a typical professional, and explains it to fans and analysts through AI agents on Microsoft Foundry. It is an entry for the Microsoft x Premier League "Inside the Game" hackathon.

All match data is **synthetic**: we built a generator whose players get tired according to published sports science, with a hidden "true" fatigue we use to test our estimator.

**Try it:** https://happy-bay-06ca1e90f.3.azurestaticapps.net/?match=story (the story match, fan mode; the favourite is the left-back the story is about).
It opens on the **Highlights**: each clip plays once as it happened (Watch), then again at half speed with its numbers (Replay with details); "Full match" is the whole replay.
Add `?match=natural`, `&mode=analyst`, `&view=full&t=<seconds>`, `&hl=<kind>&step=replay` or `&theme=dark` to the address.

- Project plan: [docs/PLAN.md](docs/PLAN.md)
- Build plan: [docs/BUILD_PLAN.md](docs/BUILD_PLAN.md)
- Evidence base (74 papers): [docs/RESEARCH_SYNTHESIS.md](docs/RESEARCH_SYNTHESIS.md); citation keys such as [Leifsson2024] are in [docs/References.bib](docs/References.bib)
- Data format: [src/secondwind/schema.py](src/secondwind/schema.py), JSON Schemas in [schemas/](schemas/)

## How it works

1. **Generator** (`sim/`): a 10 Hz match with events, a sprint motion model [Narizuka2023], role behaviours and a hidden physiology (two short-term pools and a whole-match tank) that changes which hard runs players make.
2. **Estimator** (`engine/`): from positions alone, per player and second, the running (high-speed distance, intense spells, energy) and what it would leave a typical professional (a battery with a 10–90% band, and a calibrated chance of falling below half of it).
3. **Agents** (`agents/`): an MCP server with seven read-only tools, four agents on Foundry, and a Verifier that checks every sentence against a register of published claims.
4. **Overlay** (`app/`): the replay, the batteries, the charts and the verified feed, as static files on Azure.

## Agents

Four agents on Microsoft Foundry (Agent Framework, gpt-5-mini) turn a match into a timestamped,
verified feed (`feed.json`, synced to the replay or a video by `video_s`). They see the match
only through an MCP server with seven read-only tools, and every number comes back with its unit
and the field it came from; nothing in `agents/` can read the hidden truth. **Tactical** picks
the moments (intense spells, a defender caught on the break, second wind, fresh legs, a quiet spell
that is likely tactical rather than fatigue, flat-out runs near a player's top speed, and who's doing
the running between the two teams); **Narrator** writes from the claims register's wordings;
**Personalization** sets the fan or analyst style and puts a favourite player (and whoever came
on for him) first; **Verifier** checks every sentence before it reaches the screen.

Plain code holds the agents to what the prompts ask: each moment offers only the claims that fit
it (the "after a 5-minute spell" figure only after a spell that long, "top speed hardly drops"
only after the 75th minute), a team moment always says how the two teams compare, each general
finding is shown at most twice per feed, and "fewer touches" needs measured touch counts
(PLAN decision 25). A line tagged with a general finding whose numbers all come from the moment's
facts counts as a measured fact (decision 29).

### The Verifier

It runs fixed rules first, then an LLM pass that can only block, against the claims register
(synthesis §5) and the moment's context: a sentence that blames fatigue while the team is 3–0
up, the ball is out of play or the player has just come on must say so, and every number must be
one of the facts. The paraphrases are blocked claims in other words, and the fact checks are
sentences that do or do not agree with their facts (F1); both were written before the rules or
the prompt that could catch them and never used to tune them. On 148 test sentences
([docs/verifier_report.json](docs/verifier_report.json)):

| | Unsupported sentences caught | Valid sentences blocked |
|---|---|---|
| Rules alone | 57 / 89 (paraphrases 2 / 21, fact checks 0 / 6) | 0 / 59 |
| Rules + LLM | 86 / 89 (paraphrases 21 / 21, fact checks 5 / 6) | 2 / 59 |

The LLM still misses some sentences that contradict their facts: a second wind put down to "less
opportunity to run", a general finding about short bursts used to explain a 197-second spell, and
"his fastest run so far" for a run that was not. Before prompt revision 4 it caught 2 of the 6
fact checks. The two valid sentences it blocked use "in the red", the old name for the
typical-pro chance. The rules never block a valid sentence; the LLM pass varies by a sentence or
two from run to run. In the regenerated feeds the fact check caught real slips: numbers from an
earlier 15-minute block reused at 74:59, a "3–0 lead" copied from claim 13's example when the
score was 3–1, and "level" for a 6% difference.

The LLM prompt has been revised four times, each reported in PLAN §3.4: twice on the first
suite; once after the fourth demo feeds, where it blocked the neutral name of the post-peak window
as physiology seven times; and once (decision 29) for the new names and a fact check it writes
before each verdict. Rules added from reading the feeds: no field names on screen ("G10"),
"not only fatigue" as a statement about the player's own state (claim 33), and baselines in
words ("of the last five minutes").

## The overlay

`app/` opens on the **Highlights** (decision 29): one clip at a time, in match order, from the
match's best physical moments and the feed's moments. Each clip plays twice. **Watch** is the
moment as it happened, at normal speed, with only that player's path on the pitch (the others
dimmed), the dashed circles where a turnover matters, and one line of caption. **Replay with
details** plays it again at half speed with numbers that grow with the run (speed now, top speed,
distance, metres above 5.5 m/s, the gap timer between back-to-back runs), the run's speed second
by second, his number against the published one once the clip is over, and what the feed says
about it with each line's sources and the Verifier's verdict. Then "Next". The circles show where
the player and his two nearest opponents could get to in one second, labelled "model" (the
Fujimura–Sugihara motion model with Narizuka's fit at Δt = 1 s, radius 6.2 m [Narizuka2023,
p.5–6]). The score bar shows each team's fastest second so far.

**Full match** is the whole replay. In fan mode it shows a battery icon for the selected and
favourite players (a tick shows all of them); in analyst mode the selected player's battery trace
with its band and his high-speed running. To keep one obvious place to look, the player the
current feed line is about gets a ring and that line sits under the pitch; the flat-out pulse
(90% or more of his top speed so far) and the intense-spell ring show only for him, the selected
and the favourite player, and the key is folded away. Both teams' high-speed running per
ball-in-play minute is one chart, "who's doing the running". Each feed line shows its claim,
sources and the Verifier's verdict, and a toggle shows what the Verifier blocked. The overlay's
own fixed sentences (`app/src/copy.json`) pass the Verifier too. Light and dark mode; phone
layout with a 16 px gutter and no sideways scroll.

**Highlights** are measured from positions and named as football names them: **top speed**
(against the average match top speed for his position [SilvaH2025, Table 1]), the **longest
run** above 5.5 m/s (19.8 km/h) in one go and where it went (a typical high-speed run is about
19 m [Fang2024, Table 2; DiSalvo2007, p.224]), the **recovery run** (the longest high-speed run
back towards his own goal starting within 10 s of his team losing the ball, our threshold; speed
and distance only), **back-to-back runs** (three or more with 20 s or less between them, our
threshold; Premier League players usually get 51–101 s between high-speed runs, by position
[Bradley2009, Table I]), the **busiest minute** (against a published average best minute of
62 m [Leifsson2024, Table 1]) and, at the final whistle, the **most ground covered** by
whole-match players (against the Premier League average for defenders, midfielders or forwards,
9.97 / 11.59 / 10.71 km [Kavanagh2024, Table 2]; Bradley2009, Table I agrees by position within
1–8%). The story match is short (92.8 min with added time, against a usual 99.5 [Allen2025,
Table 2]), and its most ground covered is 10.2 km. The panel shows the top 3 so far, one per
player; a click opens the clip, and "Play highlights" plays the clips one after another.
Captions come from fixed templates and pass the Verifier; they describe what the player did,
never how hard he tried (claim 38). Hardest accelerations and stops are left out: tracking
systems count them about 10-fold apart (claim 32).

The demo feeds are in [docs/feeds/](docs/feeds/): the story match (seed 2028, a high press that
fades, a full-back caught on the break again and again, a fresh substitute), the same match with that full-back
as the favourite (the one the site and the video use), and a natural match (seed 2031). Story
matches are never used for validation numbers.

## What we tested and don't claim

Each of these is a sentence fans would like to read. We tested it against the hidden truth of
synthetic matches, it does not hold up from positions, and the Verifier blocks it:

- **"He is tired."** With each player's true fitness, the generator's own physiology finds the
  tired moments almost perfectly (precision 0.99); without it, the best any positions-only
  detector reaches is precision 0.24 at recall 0.1, and our battery reaches 0.17 (dev seeds 1–60,
  [validate/ceiling.py](src/secondwind/validate/ceiling.py)). The same running drains players of
  different fitness very differently. So we say what the running would cost a *typical*
  professional (claims 11 and 33).
- **"Which team is more tired."** Home-minus-away differences pick the team with more
  short-term tiredness 47–58% of the time (chance) and the team with more late-match wear at most
  68% (60 matches, [validate/teams.py](src/secondwind/validate/teams.py)). We show the measured
  running instead: team totals per ball-in-play minute, and how a gap changed (claim 35).
- **"He ran slower than he could when it mattered."** After his team lost the ball, a slow defender had no
  run asked by his role in 94% of cases and skipped one in 5%; speed tells a skipped run from no
  run asked no better than chance (AUC 0.45). We give the speed, its share of his top speed and
  what happened (claim 38).
- **"He misplaced that pass because he was tired."** Pass completion is the same before and
  after a peak spell (80.3 vs 80.5% [Fang2024, Fig. 1]) and across the match [Carling2011,
  Table I], so the generator has no passing penalty and the Verifier blocks the claim (claim 20).
- **"They won because they ran more."** Winners outrun losers only slightly (total distance
  +0.7% [Allen2026a, Table 3]) and total distance is unrelated to points [Allen2026b] (claim 30).

## Validation

**Estimator vs hidden truth.** The battery (blue, with its band) against the generator's hidden
pools (orange) for one player of a validation match; the calibration of the typical-pro chance
before and after its map (held-out matches: expected calibration error 0.009 → 0.001); and how
well anything could tell *who* is tired from positions alone (above).

![Estimator vs truth](docs/figures/estimator_vs_truth.png)

**No-fatigue control.** The same 240 synthetic matches with fatigue switched on and off. Most of
the published drop after a player's most intense spell appears even without fatigue (picking the
peak guarantees a lower value next, and play stops after peaks [Cortez2026, Table 3]); the
end-of-match decline is all fatigue.

![No-fatigue control](docs/figures/no_fatigue_control.png)

**Realism.** 240 default synthetic matches (seeds 1–240) with fatigue on, and the same matches
with fatigue off in brackets, against published numbers. Our pass bands are proposals (synthesis
§6.1). The ball-in-play, running-by-phase and home-away rows were re-run on the same 240 seeds on
2026-10-18 (before, they came from commit 7c387c7, before the professional prior; they moved by
at most 0.06 in r and 1 m/min).

| Check | Published (source) | Synthetic (no fatigue) | |
|---|---|---|---|
| Running > 4 m/s (14.4 km/h), last 15 min vs first 15 | −21% [Bradley2009, Fig. 2]; pass −10 to −30% | −20.9% (+0.4%) | pass |
| High-speed and sprint running, 2nd half vs 1st | about level [Bradley2009, p.162]; pass ±10% | −7.5 / −9.2% (+2.1 / +2.0%) | pass |
| Recovery time between hard efforts, last 15 min vs first 15 | +28% [Bradley2009, p.162–163]; pass +15 to +40% | +15.6% (−1.3%) | pass, at the edge |
| 2nd half vs 1st, by first-half load (high / moderate / low) | −12 / 0 / 0% [Bradley2013, p.4] | −15 / −7 / +1% (−5 / +6 / +9%) | close |
| Substitutes vs whole-match players, same minutes | +15% [Bradley2013, Table IV] | +34% (+15%) | above |
| High-speed running after a 5-min peak, min 1–5, vs match average | −45 −29 −13 −8 −4% [Leifsson2024, Table 1] | −69 −33 −15 −6 −1% (−65 −31 −20 −9 −1%) | minute 1 too deep, even without fatigue |
| 1-min high-speed peak | 62 m/min [Leifsson2024, Table 1] | 73 m/min (79) | about 18% above |
| Covering and recovery runs in the 5 min after a peak, vs match average | −22 to −44% and −34 to −43% [Ju2022, p.975] | −28 / −34% (−32 / −34%) | in range, also without fatigue |
| Hard runs after a peak: length, duration, speed | −23%, −32%, −3% [Fang2024, Table 2] | −20%, −18%, −2% (−18%, −16%, −2%) | shorter but not enough |
| Distance, high-speed and sprint per position | 2024/25 targets ±5% [Allen2024, Table 4; Allen2025] | all within ±5% except full-back high-intensity −5.1% and sprint distance FB +9.1, DM +6.9, CM +6.8, CF +5.2%; team sprint +8.1% | accepted gap (decision 11) |
| Time in speed bands vs real tracking (IDSSE) | ±3 points [Bassek2025; Osgnach2010] | within 0.9 points | pass |
| Ball in play | 50–63% [Kavanagh2024, p.80; Allen2026b, Table 2] | 58.9% | pass |
| Running by phase, per player slot | 133 / 145 / 63 m/min with the ball / without / stopped [Allen2026b, Table 5] | 125 / 139 / 58 (−6.1 / −4.2 / −8.4%) | pass (±10%) |
| Home and away teams move together | r = 0.68–0.75 [Allen2026a, Fig. 2]; pass 0.5–0.85 | high-speed 0.66, high-intensity 0.77, sprint 0.74; total distance 0.96 | total distance above (decision 11) |
| Energy per player and match | 61.1 ± 6.6 kJ/kg [Osgnach2010, p.174] | 58.5 ± 5.0 kJ/kg (dev seeds 1–60); real IDSSE 57.6 ± 4.5 | close |

**Same conclusions on real data.** We ran the estimator offline on the 7 real IDSSE matches
[Bassek2025] (calibration only; the data never enters the repo or the demo) and compared
conclusions, not accuracy (there is no fatigue truth there; PLAN §2.6). They agree on load,
distance per player, the battery's dips and the deep first minute after a peak. They disagree in
two places: real players faded more in the second half (high-speed running −21% vs our −9%), and
our synthetic peak spells are more intense (1-min peak 72 vs 65 m/min).

## Synthetic-data card

One paragraph per dimension of the checklist in [RuizPinto2026, Table 3].

**Objective.** The data exists to test an estimator of how much hard running players have done
and what it would cost a typical professional, against a fatigue state that real matches never
reveal. It is not meant to stand in for real matches in any other analysis.

**Structure.** Four files per match: 10 Hz tracking of 22 players and the ball (positions in
metres, ball in or out of play, possession), events (passes, carries, receptions, shots with xG,
duels, pressures, substitutions and more, each with a phase of play), metadata (line-ups,
positions, substitutions) and, for validation only, the hidden truth (two short-term pools and a
whole-match tank per player per second, the purpose of each run and the runs a tired player
skipped). Story matches deliberately hold more tired moments than natural ones, a class-imbalance
choice [RuizPinto2026]; they are only used for the demo, and precision and recall come from
natural matches.

**Generation.** A phase-of-play state machine, a sprint motion model [Narizuka2023] limited by
each player's acceleration–speed profile [Morin2021, Table 1], role behaviours (covering,
recovery runs, pressing), position noise of 0.05 m, and a hidden physiology from published
studies [Chorley2023; Bradley2009; Fang2024; Ju2022]. Players are drawn from a typical
professional population (critical speed 4.1 ± 0.3 m/s (14.8 km/h), D′ 180 ± 54 m; decision 13).
Effect sizes we could not find in the literature are labelled "our assumption" in
`sim/params.py`. Every match regenerates from its seed.

**Constraints.** Fatigue changes which hard runs players make and how long and fast they are; it
does not change passing accuracy, decisions or shooting, because the studies find no such effect
in matches [Fang2024; Carling2011]. Top speed and acceleration fall by at most 5% [Bradley2009,
p.163; SilvaJR2018, Table 5]. Players do not pace themselves, so the late-match fade is all
physiology; in real matches part of it is the player's choice [Snyder2023].

**Utility and fidelity.** The realism table above: the end-of-match decline, the halves,
substitutes, running by phase and real speed distributions are within their bands; the drop
after a peak spell is too deep (even without fatigue), peak spells are about 12–18% too intense,
and team sprint distance is 8% high. A no-fatigue control (the same seeds with fatigue off)
separates what is fatigue from what is selection. On real IDSSE matches the estimator reaches
the same conclusions except for the size of the second-half fade.

**Risk and deployment.** This shows that the estimator recovers fatigue under the published
effects we built in; it does not prove those effects in this league. A model tuned only on this
data would learn our assumptions. So the product claims only what survives that limit (the
running, and what it would cost a typical professional), the Verifier blocks the rest, and every
screen says the match is synthetic. No real player data is distributed: IDSSE (CC BY 4.0) was
used offline for calibration only.

## Limitations

- Our synthetic players don't pace themselves, so the generator's late-match fade is all
  physiology; in real matches part of it is the player's choice [Snyder2023; synthesis §8.1].
- The typical-pro chance is calibrated for a typical professional (dev seeds, professional
  prior). On matches with a wider range of players it stays poorly calibrated (expected
  calibration error 0.064 → 0.059), because a typical-pro signal cannot see who is less fit.
- On the 7 real IDSSE matches [Bassek2025] real players faded more in the second half than ours
  (high-speed running −21% vs −9%) and our synthetic peak spells are about 12% more intense
  (PLAN §2.6).
- The Verifier's LLM pass varies from run to run, and the feed's wording with it; the rules give
  the same verdict every time. The committed demo feeds are one run each.
- Player fitness (critical speed, D′) can't be measured from tracking; the professional prior is
  derived from published tests [Modric2020, Table 1; Jones2017], and no professional D′ has been
  published (synthesis §3.2.3).
- The overlay replays files; the live stream (Event Hubs) was cut (BUILD_PLAN §5).
- The same seed gives a slightly different match on another machine (floating point), so the
  overlay ships the exported demo data (`app/public/data/`) rather than regenerating it.

## Development

```bash
uv sync --all-extras                 # Python 3.12 environment
uv run pytest                        # tests
uv run ruff check . && uv run ruff format --check .
uv run python -m secondwind.schema   # re-export JSON Schemas after changing the models
uv run python -m secondwind.sim --seed 1 --out data/synthetic/m0001   # generate one match
uv run python -m secondwind.sim.summary data/synthetic/m0001          # summarise it
uv run python -m secondwind.sim.replay data/synthetic/m0001 --start 12:00 --purposes  # replay.html
uv run python -m secondwind.sim.batch --seeds 1-30 --json report.json # means over 30 matches
```

Calibration against IDSSE [Bassek2025] (offline only; the data never goes into the repo or the
demo): `uv sync --extra calib`, `uv run python scripts/fetch_idsse.py` (~2.4 GB), then
`uv run python -m secondwind.sim.idsse` once (writes small derived files next to the raw data in
the git-ignored `data/raw/idsse/`), and add `--idsse` to `sim.batch` to compare speed and
acceleration bands. Replay as a GIF or still frames needs matplotlib (`--extra replay`), then add
`--gif` or `--stills 6`.

Estimator and validation:

```bash
uv run python -m secondwind.engine data/synthetic/m0001                 # signals.json
uv run python -m secondwind.validate.batch data/synthetic/validation    # estimator vs truth
uv run python -m secondwind.validate.calibrate data/synthetic/dev       # refit the chance map (dev seeds only)
uv run python -m secondwind.validate.real data/synthetic/dev --jobs 4   # IDSSE vs synthetic
uv run python -m secondwind.validate.figures                            # docs/figures/*.png
```

Agents (`uv sync --extra agents`; Foundry settings in `.env`, keyless auth via `az login`):

```bash
uv run python scripts/foundry_smoke.py                                  # model access, quota, latency
uv run python -m secondwind.agents.mcp_server data/synthetic/demo/story # MCP server (stdio)
uv run python -m secondwind.agents.feed data/synthetic/demo/story --favourite H04  # feed.json (add --offline)
uv run python -m secondwind.agents.highlights data/synthetic/demo/story # physical highlights
uv run python -m secondwind.agents.verifier_suite --llm --json docs/verifier_report.json
scripts/demo.sh                                                         # both demo matches + feeds
```

Overlay (React + Vite, Node 20+) and deployment (Azure Static Web Apps, Free plan):

```bash
cd app && npm install && npm run dev   # http://localhost:5173/?match=story&mode=analyst&player=H04&t=3500
scripts/deploy_site.sh                 # build app/ and deploy the committed data
```

## License

MIT. See [LICENSE](LICENSE).
