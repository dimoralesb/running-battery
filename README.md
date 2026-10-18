# Second Wind

> The story the scoreline doesn't tell: who has done the most hard running, and when it costs them.

Second Wind measures from tracking data how much hard running each football player has done and what it would cost a typical professional, and explains it to fans and analysts through AI agents on Microsoft Foundry. It is an entry for the Microsoft x Premier League "Inside the Game" hackathon.

All match data is **synthetic**: we built a generator whose players get tired according to published sports science, with a hidden "true" fatigue we use to test our estimator.

**Status:** in development (October 2026).

- Project plan: [docs/PLAN.md](docs/PLAN.md)
- Build plan: [docs/BUILD_PLAN.md](docs/BUILD_PLAN.md)
- Evidence base (74 papers): [docs/RESEARCH_SYNTHESIS.md](docs/RESEARCH_SYNTHESIS.md)
- Data format: [src/secondwind/schema.py](src/secondwind/schema.py), JSON Schemas in [schemas/](schemas/)

## Development

```bash
uv sync                          # Python 3.12 environment
uv run pytest                    # tests
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
acceleration bands.

Replay as a GIF or still frames needs matplotlib: `uv sync --all-extras` (or `--extra replay`),
then add `--gif` or `--stills 6`. Add `--clean-copy` when generating to keep the noise-free positions for debugging
(`debug/tracking_clean.npz`; not part of the match data).

Estimator and validation (`uv sync --all-extras` for IDSSE and the charts):

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
uv run python -m secondwind.agents.feed data/synthetic/demo/story       # feed.json (add --offline)
uv run python -m secondwind.agents.verifier_suite --llm                 # Verifier report
scripts/demo.sh                                                         # both demo matches + feeds
```

Overlay (React + Vite, runs locally from files; Node 20+):

```bash
uv run python -m secondwind.export data/synthetic/demo/story --out app/public/data/story --feed docs/feeds/story.json
uv run python -m secondwind.export data/synthetic/demo/natural --out app/public/data/natural --feed docs/feeds/natural.json
cd app && npm install && npm run dev   # http://localhost:5173/?match=story&mode=analyst&player=H04&t=3500
```

## Agents

Four agents on Microsoft Foundry (Agent Framework, gpt-5-mini) turn a match into a timestamped,
verified feed (`feed.json`, synced to the replay or a video by `video_s`). They see the match
only through an MCP server with seven read-only tools, and every number comes back with its unit
and the field it came from; nothing in `agents/` can read the hidden truth. **Tactical** picks
the moments (red-zone spells, a defender exposed on the turnover, second wind, fresh legs, a drop
that is tactical rather than fatigue, flat-out runs near a player's top speed, and the tug of war
between the two teams' running); **Narrator** writes from the claims register's wordings;
**Personalization** sets the fan or analyst style; **Verifier** checks every sentence before it
reaches the screen.

The Verifier runs fixed rules first, then an LLM pass that can only block, against the claims
register (synthesis §5) and the moment's context: a sentence that blames fatigue while the team
is 3–0 up, the ball is out of play or the player has just come on must say so, and every number
must be one of the facts. On 120 test sentences ([docs/verifier_report.json](docs/verifier_report.json)):

| | Unsupported sentences caught | Valid sentences blocked |
|---|---|---|
| Rules alone | 52 / 74 (paraphrases 2 / 21) | 0 / 46 |
| Rules + LLM | 74 / 74 (paraphrases 21 / 21) | 0 / 46 (2 in the previous run) |

The overlay (`app/`) replays the match with a battery icon per player (fan mode) or the selected
player's battery trace with its band and his high-speed running (analyst mode), and both teams'
running per ball-in-play minute, next to the feed; each line shows its claim, sources and the Verifier's verdict, and a toggle shows what the
Verifier blocked. Its own fixed sentences (`app/src/copy.json`) pass the Verifier too.

The demo feeds are in [docs/feeds/](docs/feeds/): a story match (seed 2028, a high press that
fades, a full-back exposed on turnovers, a fresh substitute) and a natural one (seed 2031). Story
matches are never used for validation numbers.

What we do not claim, because we tested it and it does not work from positions
([validate/teams.py](src/secondwind/validate/teams.py), 60 synthetic matches with the hidden
truth): **which team is more tired** (the estimator picks the team with more late-match wear
in at most 68% of matches, and with more short-term tiredness at chance level), and **whether a
player ran slower than he could when it mattered** (a slow defender after a turnover had no run
asked by his role in 94% of cases, and a skipped run in 5%). We show the measured running
instead: team totals per ball-in-play minute, top speeds, and how a gap changed.

## Validation

**Estimator vs hidden truth.** The battery (blue, with its band) against the generator's hidden
pools (orange) for one player of a validation match; the calibration of the typical-pro chance
(`low_chance`) before and after its map; and how well anything could tell *who* is tired from
positions alone. With each player's true fitness the generator's own physiology finds the tired
moments almost perfectly (precision 0.99); without it, the best possible precision is 0.24 at
recall 0.1, and our battery reaches 0.17. That gap is why Second Wind reports the running and
what it would cost a typical professional, never "he is tired".

![Estimator vs truth](docs/figures/estimator_vs_truth.png)

**No-fatigue control.** The same 240 synthetic matches with fatigue switched on and off. Most of
the published drop after a player's most intense spell appears even without fatigue (picking the
peak guarantees a lower value next, and play stops after peaks); the end-of-match decline is all
fatigue.

![No-fatigue control](docs/figures/no_fatigue_control.png)

## Limitations

- Our synthetic players don't pace themselves, so the generator's late-match fade is all
  physiology; in real matches part of it is the player's choice [Snyder2023; synthesis §8.1].
- The typical-pro chance is calibrated for a typical professional (dev seeds, professional
  prior). On matches with a wider range of players it stays poorly calibrated (expected
  calibration error 0.064 → 0.059), because a typical-pro signal cannot see who is less fit.
- On the 7 real IDSSE matches [Bassek2025] the estimator's load, distances and battery dips look
  like the synthetic ones, but real players faded more in the second half (high-speed running
  −21% vs −9%) and our synthetic peak spells are about 12% more intense (PLAN §2.6).
- The Verifier's LLM pass varies from run to run (on the suite, 2 of 40 valid sentences blocked in
  the final run, 7 in the first), and the feed's wording with it; the rules give the same verdict
  every time. The committed demo feeds are one run each.
- Player fitness (CS, D′) can't be measured from tracking; the professional prior is derived from
  published tests, and no professional D′ has been published (synthesis §3.2.3).

## License

MIT. See [LICENSE](LICENSE).
