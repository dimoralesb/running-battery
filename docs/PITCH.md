# Running Battery: pitch text for the submission form

The rules ask for "a short elevator pitch for your Project including what you built, which
Microsoft and Azure technologies used, what it does, what problem it solves" (OFFICIAL RULES
§4.4); they set no length. Every sentence below passes the Verifier's rules
(`tests/test_pitch.py`); the sources are in the table at the end.

## Short version (one paragraph)

Running Battery shows the story the scoreline doesn't tell: who has done the hard running, when, and
what it would cost a typical professional. From tracking positions alone it measures each
player's high-speed running, top speed and hardest minutes, and four AI agents on Microsoft
Foundry turn that into a timed, verified feed for a fan or an analyst. A Verifier checks every
sentence against 46 claims from published sports science before it reaches the screen. The match
data is synthetic, from a generator with a hidden fatigue model we use to test what positions can
and cannot tell.

## Full version

**What it is.** Running Battery is an overlay and a team of AI agents that explain the running in a
football match. It opens on the match's highlights: each clip plays as it happened, then shows
its numbers and what the agents say about it, each line with its sources and the Verifier's
verdict; a replay button plays it again.

**The problem.** Broadcasts show distance covered, but not when the hard running happened, what
it would cost, or whether the story told about it holds up. Fatigue talk is easy to get wrong.
The same running costs players of different fitness very different amounts, and tracking data
cannot tell their fitness apart.

**What is measured and what is estimated.** Measured from positions: speed, distance, metres
above 5.5 m/s (19.8 km/h), each player's hardest minutes so far, and each team's high-speed
running per ball-in-play minute, split by situation (the first 10 s after losing or winning the
ball, settled on the ball, without it). Estimated: what that running would leave a typical
professional, with a 10–90% band and a calibrated chance of falling below half of it (expected
calibration error 0.008 to 0.001 on held-out matches).

**What we tested and don't claim.** We built a match generator whose players have a hidden
fitness and fatigue state, and tested the sentences fans would like to read against it. From
positions, the best detector of tired players reaches precision 0.11 at recall 0.1, so we say what the running would cost a typical professional and never name a player's own
state. Home-minus-away differences pick the side with more short-term fatigue 52–55% of the time,
no better than chance. Speed tells a skipped run from no run asked with an AUC of 0.42, so we give
the speed and never the intent. Reading a run's purpose failed too: a positions-only rule built on
a published definition matched the generator's hidden runs with precision 0.30, so the split
shows where the running happened, never why. The Verifier
blocks all four.

**The Microsoft stack.** Four agents on Microsoft Foundry (gpt-5-mini) with Microsoft Agent
Framework: Tactical picks the moments, Narrator writes them from the claims register,
Personalization sets the fan or analyst style, and the
Verifier runs fixed rules and then an LLM pass that can only block. The agents see the match only
through an MCP server with seven read-only tools, and every number comes back with its unit and
source. The overlay (React) is hosted on Azure Static Web Apps; auth is keyless (Entra ID); CI
runs on GitHub Actions.

**How we checked it.** The generator is grounded in 74 papers and checked against 240 synthetic
matches and 7 real tracked matches (IDSSE, offline calibration only). On 192 test sentences, the
rules alone never block a valid sentence, and rules plus the LLM catch most unsupported ones
(README, The Verifier).

**Try it:** https://happy-bay-06ca1e90f.3.azurestaticapps.net/?match=story

## Sources

| Statement | Source |
|---|---|
| 46 claims (14 supported, 14 qualified, 18 blocked) | `src/runningbattery/agents/claims.json`; synthesis §5 |
| 5.5 m/s (19.8 km/h) high-speed threshold | README "The overlay"; `engine/params.py` |
| 10–90% band, calibrated chance; ECE 0.008 to 0.001 | PLAN decision 15; README "Validation" |
| Precision 0.11 at recall 0.1 for the best positions-only detector | README "What we tested"; `validate/ceiling.py`, dev seeds 1–60 |
| Home-minus-away right 52–55% of the time | PLAN decision 23; `validate/teams.py`, 60 matches |
| AUC 0.42, skipped run vs no run asked | PLAN decision 24; `validate/teams.py` |
| A run's purpose (closing down, on Ju2022's definition): precision 0.30 | PLAN decision 30; `validate/purposes.py`, 75,820 runs |
| 10 s after a change of possession | our threshold; transitions last 9.3–10.9 s [Bortnik2022, Table 2] |
| Seven read-only MCP tools | `src/runningbattery/agents/mcp_server.py` |
| gpt-5-mini on Foundry | PLAN decision 18 |
| 74 papers; 240 matches; 7 IDSSE matches | README; [Bassek2025] |
| 192 test sentences; rules never block a valid one | `docs/verifier_report.json` |
