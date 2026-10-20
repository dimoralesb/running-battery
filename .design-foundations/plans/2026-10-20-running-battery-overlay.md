# Plan: Running Battery overlay as a cleaned-up broadcast

- Date: 2026-10-20 · Track: **Quick** · Entry stage: **Discover** (no DESIGN.md or JOURNEY.md yet)
- **Status:** in-progress · **Started:** 2026-10-20 · **Current Phase:** 1 · Branch: `redesign`
- Seed: `.design-foundations/research/2026-10-20-running-battery.md`

## Context

**Problem:** Redesign the overlay (`app/`) as a cleaned-up TV broadcast for judges on a laptop:
while a clip plays, only the score bug and one lower third (moment, player, battery); when the
clip ends, its details open in the Feed tab under the pitch; Clips, Team sheet, Feed and Settings
live in tabs under the pitch, one at a time. The battery is the brand and the one bold graphic.

**Constraints:**
- Decision 14: every battery says it is what the running would leave a typical professional,
  never the player's own state. Every on-screen sentence (incl. `app/src/copy.json`) passes the
  Verifier. Football's words ("his hardest minutes", no "pressing", teams in full, m/s then km/h).
- React 18.3.1 + Vite 5.4.11 + TypeScript, static on Azure Static Web Apps (Free).
- Every URL parameter keeps working (`view`, `match`, `t`, `mode`, `player`, `favourite`, `theme`,
  `batteries`, `hl`, `moment`, `item`, `step`, `auto`).
- Dark by default, light available. Phone 360/390 px: no sideways scroll.
- No third-party marks. Goalkeepers get no battery. Analyst mode keeps the 10–90% band.
- About six days to Tue 27 Oct 2026; the demo video follows the build.

**Taste signals (dealer pins, from research):**
- Broadcast over editorial or "quiet app".
- The battery carries the identity, not colour blocks or panels.
- No all-caps condensed labels in boxes everywhere (the current Barlow Condensed look); capitals
  only in the score bug.
- Keep the mown green pitch with white lines and the two validated team colours.
- One modern, slightly squared sports sans in mixed case, with bold tabular numbers.

**Defaults taken (user may object):** "fastest so far" moves to the top of the Clips tab; the full
match view uses the same frame (score bug, lower third, play bar, tabs).

**Mock sign-off (2026-10-20, wireframe, `.design-foundations/mocks/`):** layout approved. Carry
into the build: (1) a **shorter pitch**, so the tabs and the first lines of the details show at
1440×900 without scrolling; (2) Previous enabled whenever there is a previous clip; (3) the stat
says "his team lost the ball", as the feed line does; (4) fans see a short verdict label
("Verified · published research"), and a click shows the claim and papers; analysts see the full
citation; (5) team colours plus a colour chip in the score bug say which markers are which team;
(6) the brand's battery mark is an outline or full, never a second reading; (7) 360/390 px with
no sideways scroll, gauge and percentage visible; (8) the run trace shows its direction (arrowhead
or fading tail). Minor: no repeated values in Details, Replay and Next equal weight, the lower
third clear of the touchline. Review: `.design-foundations/build/2026-10-20-running-battery-overlay-mock-review.md`.

**Success criteria:** at first sight a judge sees the pitch and one bar and nothing else competes;
every current feature is reachable through a tab; text passes WCAG AA in both themes; no boxed
all-caps labels outside the score bug; the user signs off a mock before the build.

## Phase 1: Screen spec
**Stage:** Discover
**Model:** sonnet
**Doctrine:** journey, usability
**Gate:** Standard

**Goal:** Specify what is on screen in each step and what each tab holds.

**Scope:**
- IN: the frame (score bug, pitch, lower third, play/clip controls, tabs); steps Watch, Details,
  Replay, Full match; tabs Clips, Team sheet, Feed, Settings (view, match, Fan/Analyst, favourite,
  theme); laptop (1280–1440 px) and phone (360/390 px) layouts; which tab opens on which step.
- OUT: changes to the data, the agents' lines or the science; new features.

**Edge cases:** a clip about a team (no player, so no battery: the lower third shows both teams'
running); a goalkeeper clip; a clip merged into another; `step=details` deep link must open the
Feed tab; `auto=1` must advance without the user touching a tab; analyst mode adds the band in
the lower third without a second row on a phone.

**Produces:** JOURNEY.md `## Page specs` (one entry: the overlay, with its four steps and four tabs).
**Depends on:** research doc | **Unlocks:** Phase 2

**Done when:**
- [ ] DW-1.1: JOURNEY.md `## Page specs` has a complete entry for the overlay covering Watch, Details, Replay and Full match.
- [ ] DW-1.2: every element of today's overlay is mapped to a place (frame or a named tab) or listed as dropped with a reason.
- [ ] DW-1.3: every current deep link maps to the screen and tab it opens.
- [ ] DW-1.4: heuristic pass: during Watch, only the score bug, pitch and lower third carry emphasis; the play controls and the tab bar stay quiet (low emphasis, no saturated colour).

## Phase 2: Visual identity
**Stage:** Design
**Model:** fable
**Doctrine:** design-dna, fonts, color, data-viz, ai-tells
**Gate:** Full

**Goal:** Lock the look: the type pairing, colour tokens for both themes, and the battery as mark and gauge.

**Scope:**
- IN: font choice (Google Fonts only), type scale, colour tokens (dark default + light), team
  colours carried over, the battery mark (logo) and gauge spec (fill, band, percentage), score bug,
  lower third, tab bar styles.
- OUT: the pitch geometry and player markers (kept), chart internals beyond tokens.

**Constraints:** the taste signals above; team colours stay the validated dataviz pair; the
battery gauge is the only saturated element outside team colours.
**Edge cases:** battery near 0% or 100% stays readable; the band in analyst mode; light theme
over the green pitch; contrast of white text on both team colours.

**Produces:** DESIGN.md **locked** (token block + type scale + battery spec), user-confirmed.
**Depends on:** Phase 1 | **Unlocks:** mock, then build

**Done when:**
- [ ] DW-2.1: DESIGN.md locked (token block present + user-confirmed).
- [ ] DW-2.2: all text/background pairs pass WCAG AA (≥4.5:1 body, ≥3:1 large) in dark and light, verified via `palette.mjs`.
- [ ] DW-2.3: interactive elements and the battery fill pass AA non-text (≥3:1) against their background.
- [ ] DW-2.4: semantic aliases resolved (`--background`, `--surface`, `--text`, `--accent-solid`) and type scale `--text-xs`…`--text-4xl` present.
- [ ] DW-2.5: no all-caps outside the score bug; numbers use tabular figures.

## Verification plan

- DW-1.1–1.4: read JOURNEY.md against today's overlay (screenshots of Highlights, Full match, phone).
- DW-2.1–2.5: `palette.mjs` on every pair, both themes; token list check.
- Dirty cases: a Design page laid out before JOURNEY.md page specs exist → stop (gate 1); tokens or
  a styled mock before DESIGN.md is locked → stop (gate 2); a team-colour/white pair below 4.5:1 →
  token rejected or text made large/bold; a team clip with no player → lower third spec must not
  show an empty battery.
- Then mock (`/design-for-ai:mock`), user sign-off, build in `app/`, Verifier on new copy, light/dark
  and 360/390 px checks, decision 36.

## Execution log

### Phase 1: Screen spec (Gate: Standard)
- [x] BUILD: Discovery + design + production complete (sonnet)
- [x] REVIEW: PASS (haiku; one Major: the tab named "Feed" is weak scent for a clip's details)
- [x] Committed
Summary: JOURNEY.md holds the overlay's page spec (Watch, Details, Replay, Full match; tabs Clips, Team sheet, Feed, Settings), maps every current element and all 13 URL parameters, lists new copy to verify (incl. the analyst trace tooltip, which lacked "typical professional"), and leaves seven defaults open for sign-off.
