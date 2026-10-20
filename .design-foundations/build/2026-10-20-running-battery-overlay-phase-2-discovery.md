# Discovery + Design: Phase 2 - Visual identity

Plan: `.design-foundations/plans/2026-10-20-running-battery-overlay.md` · Date: 2026-10-20 · Mode: Full

## Artifacts Found / Current State

- **DESIGN.md:** absent. This phase writes it (status "ready to lock", awaiting the user).
- **JOURNEY.md:** present (Phase 1, committed 285a19a). Page spec for the overlay: Watch, Details, Replay, Full match; tabs; layouts; the Watch heuristic table (score bug, pitch, lower third carry emphasis; play bar and tabs quiet, no saturated colour).
- **Today's look (`app/src/styles.css`, `app/index.html`):** Barlow + Barlow Condensed (all-caps display face on buttons, headings, bug, lower third, stats); navy-tinted neutrals (`--page #0a0c10`, `--surface #151922`, `--bug #1a2132`); team colours light `#2a78d6`/`#eb6834`, dark `#3987e5`/`#d95926`; warning `#fab219`; grass light `#3b7638`/`#43803f`, dark `#1e4622`/`#224e27`; light theme on `:root`, dark via `prefers-color-scheme` and `[data-theme="dark"]`.
- **Wireframe mock:** `.design-foundations/mocks/running-battery-{watch,details}.html` + PNGs (greyscale, layout signed off). Generator: scratchpad `gen_mock.py`.

## Gaps

1. **White text on the team colours fails 4.5:1** (measured with the palette.mjs formula): white on `#2a78d6` 4.42, on `#3987e5` 3.64, on `#eb6834` 3.20, on `#d95926` 3.88. Today's shirt numbers on markers and `.sheet-shirt` badges are white on team colour.
2. **Team markers vs grass fail 3:1**: on light grass `#3b7638` home 1.24, away 1.71; on dark grass `#1e4622` home 2.95, away 2.77. The hardest-minutes ring `#fab219` on light grass is 2.99.
3. **Light theme over the pitch** has no rule today (the pitch changes with the theme and the light pitch is where markers fail).
4. **Outlined buttons**: palette `--border-strong` (light `#a6ada5`) is 2.25:1 on the page: too weak for an outline that marks a control.
5. **No DESIGN.md**, so no `--text-xs`…`--text-4xl`, no semantic aliases.
6. The user's three sign-offs (tab "Details", narrow column, "synthetic match" in the brand line) are not in JOURNEY.md yet.

## Gate Status

- JOURNEY.md present: YES (page spec complete; Phase 1 reviewed PASS).
- DESIGN.md locked: NO, this phase produces it. The styled mock is produced against the ready-to-lock DESIGN.md so the user can lock on real pixels (the dispatch asks for it); app/ is not touched.
- Prerequisites met: YES.

## DW Verification

| DW-ID | Done-When Item | Status | Evidence |
|-------|---------------|--------|----------|
| DW-2.1 | DESIGN.md locked (token block + user-confirmed) | COVERED (token block); confirmation pending by design | DESIGN.md with a full `:root` (dark default) + `:root[data-theme="light"]` token block, marked "ready to lock, awaiting user confirmation"; the orchestrator asks the user |
| DW-2.2 | all text/background pairs pass AA in dark and light, via palette.mjs | COVERED | `palette.mjs --seed "#3b7638" --chroma muted --harmony mono` exit 0 (neutral ramps both schemes) + `check-contrast.mjs`, which uses palette.mjs's exact WCAG formula, parses DESIGN.md's token block and checks every text pair (page, plates, pitch, team colours) in both themes; exits non-zero on any miss |
| DW-2.3 | interactive elements and battery fill ≥3:1 against their background | COVERED | same script: non-text pairs (tab underline, focus ring, outlined-button edge, team dots/chips, battery fill vs plate, fill vs empty track, shell, band ticks, markers vs grass, trail, warning ring) |
| DW-2.4 | aliases `--background --surface --text --accent-solid` + `--text-xs`…`--text-4xl` | COVERED | token block present in DESIGN.md and wired into the mock's `:root`; the script asserts each name resolves in both themes |
| DW-2.5 | no all-caps outside the score bug; tabular figures | COVERED | rule in DESIGN.md; the mock's CSS has `text-transform: uppercase` only under `.scorebug`; `font-variant-numeric: tabular-nums` on every numeric class; Saira's `tnum` feature verified in the font file (GSUB has `tnum`) |

DW-IDs in table: 5 · DW-IDs in prompt: 5.
**All items COVERED:** YES (DW-2.1's user confirmation is by construction the orchestrator's step).

## Design Decisions

**Grounding.** A TV channel's on-screen graphics (one dark plate at a time over the picture, capitals only in the score bug) + a phone's battery indicator (a squared shell, a charge that fills it, the number beside it). The collision: a broadcast frame whose only graphic idea is a battery.

**Pins (user law, from the research Taste signals and the plan):** family Cinematic Dark (broadcast, dark default), composition from JOURNEY.md (signed-off wireframe), hue = the pitch green, chroma muted, signature = the battery (user's own move). The composition dealer was run with these pins: `cinematic-dark × monolith-center` is a banned tell cell ("dark default with glowing accents, centred hero"), so the hand is `cinematic-dark × frieze-bands` (variance 4): stacked horizontal bands (score bug row, pitch, play bar, tabs, panel), each its own ground, hard edges. The dealt signature (`exposed-grid`) is swapped for the user's own move (the battery), per the converge swap rule. The five-candidate diverge is not run: every axis is pinned by the user or by Phase 1, and a non-interactive build cannot present candidates (design-dna "Pins").

**Type (doctrine: fonts; ch03 + appendix).** One family: **Saira** (Google Fonts, variable 100–900, width 50–125), by Omnibus-Type. Why: its squared, superelliptic bowls are the "slightly squared sports sans" the user asked for, it reads well in mixed case at 14–16 px (large x-height, vertical axis, even texture), and the font file carries `tnum` (checked: GSUB features include `tnum`; default figures are proportional, so `tabular-nums` is set on every number). Rejected: Titillium Web and Bai Jamjuree (no `tnum` feature), Barlow (today's face; keeping it would not answer "looks like any dashboard"), Inter/Roboto (tell), Space Grotesk (tell). One family per appendix A ("start with one"); hierarchy by size and weight (400/500/600/800), capitals only in the score bug at weight 700 with +0.04em tracking.

**Colour (doctrine: color ch08/ch09, data-viz).**
- Neutrals from `palette.mjs` seeded on the pitch green (`#3b7638`, h 142.8, muted, mono): grey with a trace of the grass (chroma ≤ 0.018), so the frame belongs to the pitch, not to navy.
- **The battery is drawn in "charge": the ink of the ground it sits on.** On the dark plates (both themes) the charge is a near-white `#f4f6f2`; on the light page (Team sheet) it is the text colour. Every hue was eliminated: blue and orange are the teams, amber is "hardest minutes", green is the pitch and "good", red is "low/danger" (decision 14: the gauge must never look like a status), violet sits on the purple tell triplet and next to the blue team under deuteranopia, magenta/cyan evoke a league's trade dress and the cyan-on-dark tell. The identity is the shape (research: "the battery shape is the logo"), and white-on-dark is what broadcast graphics use. `--accent-solid` resolves to the charge. The palette's green accent ramp is not used in the UI (it would be a second saturated element; plan constraint).
- **Team colours: the value is chosen by the ground, not the theme.** On dark grounds (pitch, plates, dark page) the validated dark-mode pair `#3987e5`/`#d95926`; on the light page the validated light-mode pair `#2a78d6`/`#eb6834`. Values unchanged.
- **Text on team colours is dark, never white** (`--on-team: #121312`: 5.12 on `#3987e5`, 4.80 on `#d95926`). White fails on all four values (gap 1). The Team sheet's shirt badge becomes plain text with a team chip (no colour block).
- **The pitch does not change with the theme** (it is the picture; the plates on it are dark in both themes). Grass darkened a little, from `#1e4622`/`#224e27` to `#173a1b`/`#1a3e1e`, so both team markers clear 3:1 (gap 2); still mown green with white lines.
- **The run trail is white** (`--trail`), not the team colour (team colour on grass is 1.2–3:1), as in the signed-off wireframe; direction by an arrowhead at the player.

**Data-viz (gauge).** Position/length on a common scale is the most accurate channel (Cleveland & McGill 1984): the gauge is a horizontal length from a fixed zero, with the number beside it (redundant encoding, not colour). One colour at every level (no red at low values: colour must not encode a judgement; decision 14). Analyst band as two brackets that stand above and below the shell (it is a range, not a second fill). Data-ink: no gradient, no glow, no segments.

**AI tells scan (ai-tells).** Avoided: Inter/Roboto/Space Grotesk; cyan-on-dark; purple triplet; glow on dark; nested cards (panels are rules and rows, no cards); uniform shadows (none); pure `#000`/`#fff` everywhere (only `#fff` on the pitch lines/trail). Risk named: dark default (justified: broadcast medium, user's sign-off; no glowing accents).

**Tools reused.** `palette.mjs` for neutrals and functional colours; a small check script with palette.mjs's own contrast formula for the broadcast layer (palette.mjs only reports its own ramp pairs); the wireframe generator adapted for the styled mock; headless Chromium for PNGs (no browser MCP).

## Recommendation

BUILD
