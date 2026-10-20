# Design Review: Phase 1 - Running Battery overlay (JOURNEY.md spec)

## Rendered Evidence (Step 0)
- Screenshot: none. Spec-only phase; no rendered page was supplied. Structure-level critique of JOURNEY.md, cross-checked against the code in `app/src/` (App.tsx, Battery.tsx, copy.json). Pixel-level contrast and spacing are unverified for the build; the wireframe PNGs in `.design-foundations/mocks/` were not used as evidence.
- Surface: JOURNEY.md `## Journey`, `## IA`, `## Flows`, `## Page specs` (The overlay, Layouts, States, Edge cases, Heuristic pass, Element map, Deep links, New copy, Open for sign-off).

## Assessment B — Deterministic Detector
- Command: not run. No `.html` or mock was supplied; the artifact is `JOURNEY.md`.
- Exit: N/A (no rendered artifact).
- Findings: N/A — no rendered artifact.
- Opened only after Assessment A findings were frozen: N/A

## Triage
- Baseline (always-on): visual + usability.
- Dispatched: `journey` (the surface is a route through time and a page spec: Watch → Details → Replay → Full match, plus tab flows); `usability` (the surface is operated: tabs, play bar, deep links).
- Not applicable: `data-viz` (no chart spec beyond inherited charts; charts are carried over unchanged); `content-design` (new copy table is checked only where it bears on the Edge cases and DW items); `behavioral` / `deceptive-patterns` (not a persuasion surface; the "never tired" constraint is checked under the DW items).
- Deferred: `visual` doctrine not loaded; it is not a DW item and the spec has no visual tokens (DESIGN.md is Phase 2).

## Cross-Pillar Findings (ONE ranked report)
| Severity | Pillar | Problem | Principle | Fix |
|----------|--------|---------|-----------|-----|
| Major | usability | The Details step's only route to the evidence is a tab named "Feed". The spec's own IA note (line 53 and open item 2) rates "Feed" as weak scent for this job, yet the Details job ("Why is this a moment? Can I trust it?", line 26) depends on it. | Nielsen #2 (match with the real world); Rosenfeld/Morville local-nav labelling; usability Rule "cite the principle" (scent) | Decide before Phase 2 sign-off: rename to "Details" or add a Details-named link in the play bar's status text. Not a FAIL: the spec flags it and the requirements do not list it. |
| Minor | usability / journey | Auto mode flips the visible tab every cycle with no user action: Clips during Watch, Feed during Details (lines 59, 190, 303). The viewer's panel content changes about every 6 s plus clip length. | Nielsen #1 (visibility of system status) and change blindness (the spec cites it for the "Clip ended" flag, line 243); Hick-style choice load is not the issue here | State in the JOURNEY.md that auto mode's tab flip is intended, or hold the tab during auto. Not a FAIL: `auto=1` advances without a tab touch as required. |
| Minor | visual / usability | DW-1.4 says "only the score bug, pitch and lower third carry emphasis" during Watch. The spec's own table (line 210) gives the Clips panel's "Now playing" row weight 600 and a light neutral fill, and the selected tab weight 600 (line 209). The tab bar still uses no saturated colour, so the literal "only" is narrowly exceeded. | Von Restorff (the one thing that differs is remembered), Nielsen #8 (nothing irrelevant competes) | Either state that the selected tab and the playing row are the two allowed state marks, or drop weight 600 on the playing row and keep the fill alone. |
| Minor | journey | The Details state needs the Feed panel's first line visible at 1440×900 (line 105). The pitch budget arithmetic checks out (72 + 570 + 44 + 48 + gap ≈ 746), but at 1280×720 the visible panel is about 150 px and the spec does not state the first line is visible there. | Fitts / visibility of the fold (usability); journey Details touchpoint (line 26) | Add the 1280×720 visible content to the Details page spec. |
| Note | journey | Team-clip battery slot uses "latest finished 5-minute block" (line 187). This matches TeamChart.tsx ("in 5-min blocks") and the Details team chart uses 15-minute blocks (SplitChart). Consistent; recorded as a cross-check, not a defect. | Cross-check against code | None. |

## Requirement Fulfillment

### DW-1.1
PREMISE:  "JOURNEY.md `## Page specs` has a complete entry for the overlay covering Watch, Details, Replay and Full match."
EVIDENCE: `## Page specs` → `### The overlay` (line 71) has Purpose, Entry points, Content blocks 1–8, Step × region table (lines 90–96), Tab rules 1–4, height budget, and four step subsections: `#### Step: Watch` (109), `#### Step: Details` (115), `#### Step: Replay` (130), `#### Step: Full match` (134). Each has exit and states. Layouts, States, Edge cases and Heuristic pass follow in the same spec.
VERDICT:  PASS

### DW-1.2
PREMISE:  "every element of today's overlay is mapped to a place (frame or a named tab) or listed as dropped with a reason."
EVIDENCE: `### Element map` (lines 220–281) covers the header controls (View, Match, Fan/Analyst, Favourite player: App.tsx lines 231–268), brand and tagline (lines 224–225), score bug and fastest strip (lines 231–232, App.tsx 272–285), clip head and step chip (lines 233–235; App.tsx 290–296), pitch markers, trail, reach circles and battery icons (lines 236–242), lower third rows and gauge (lines 244–255; Battery.tsx 50–90, including the team and GK branches at Battery.tsx:19), play bar (line 256), Team sheet, Replay panel (stats, chart, compare, lines, blocked lines, team clip charts: lines 258–265; App.tsx 327–340), Full match transport, Key, moment chips, Highlights panel, player card, Trace, Feed (lines 266–278), footer, states (line 280), and unused code (line 281). Each "Dropped" row has a reason (red dot, "Ready" emphasis, Battery label, unused code).
VERDICT:  PASS

### DW-1.3
PREMISE:  "every current deep link maps to the screen and tab it opens."
EVIDENCE: The code reads 13 parameters: App.tsx lines 36–38 (theme), 53 (hl), 58–60 (moment, player), 64 (item), 69 (match), 72 (view), 76 (mode), 80 (batteries), 83 (auto), 112 (t), 115 (player), 117 (favourite), 121 (step). `### Deep links (DW-1.3)` (lines 285–305) has a row for each of the 13, with "Screen · tab it opens" and the precedence `hl` > `moment` > `item` (line 287), which matches App.tsx lines 53–65. `step=details` → Feed (line 302), matching the App.tsx start(it, "details") path. `view=full` → Full match · Feed (line 291).
VERDICT:  PASS

### DW-1.4
PREMISE:  "heuristic pass: during Watch, only the score bug, pitch and lower third carry emphasis; the play controls and the tab bar stay quiet (low emphasis, no saturated colour)."
EVIDENCE: `### Heuristic pass` table (lines 201–211): score bug, pitch, lower third = "carries emphasis"; play bar and tab bar = "quiet", "none" colour. The wireframe check (line 213) reports `class="emph"` appears 0 times in `running-battery-watch.html` (grep confirmed: 0) and `.controls` / `.tabs a` use `--text-secondary` with no fill. Caveat (Minor, see table): the selected tab (line 209) and the Clips "Now playing" row (line 210) use weight 600, which the literal "only" wording does not cover.
VERDICT:  PASS

## Edge cases (same standing as DW items)

- **A clip about a team (no player; both teams' running in the lower third):** handled. Lines 187 (battery slot shows both teams' running, `teamChartAxis`, latest finished 5-minute block, `hlNone` before the first block; star dimming off), 252 (element map). Code cross-check: Battery.tsx `reading()` returns null without a player, so the team slot is a build item, not present today.
- **A goalkeeper clip:** handled. Line 188: lower third shows "GK", no gauge, no percentage, no empty shell, no pitch battery icon. Code: Battery.tsx:19 returns null for GK; Pitch.tsx:245 excludes GK from the battery icon.
- **A clip merged into another:** handled. Line 189: plays as one-off, extra first Clips row, no "n / N", Previous/Next by match time. Build gap noted (not a spec defect): App.tsx:150–152 today gives `ix = -1`, so Previous is disabled for a merged clip.
- **`step=details` must open the Feed tab:** handled. Line 302 and line 190 (Feed, paused on last frame).
- **`auto=1` must advance without a tab touch:** handled. Lines 59, 190, 303 and tab rules 1 and 3 (lines 100–102). Minor note on the tab flip above.
- **Analyst mode adds the band without a second row on a phone:** handled. Line 169 (band bracket on the gauge's row, phone "the same, on the gauge's row"), line 251 (band sentence moved to Feed), line 191. Code today renders the band as a second row (Battery.tsx:86–88); the spec moves it, which is the intended change.

## Notes (non-blocking)
- No pixel evidence. Judgements about the phone layout, the 1280×720 fold and the tab-flip feel need the Phase 2 mock and a render.
- Judges' behaviour is UNGROUNDED (JOURNEY.md line 20). The emotion column and the "Feed" scent judgement are hypotheses, as the spec itself says.
- Journey doctrine checks passed: job story and owner, research basis and update trigger present (line 20); one JTBD school (Klement) declared (line 16); no linear funnel (line 30); Switch interview flagged NOT CONDUCTED (line 15).
- Usability doctrine checks passed: heuristics cited (Nielsen #8 at line 199; Hick–Hyman at line 36; Fitts and Jakob at line 199; Cowan at line 81); the frame's emphasis is justified by a named heuristic.
- The "Feed" tab label is the only real open usability question; it is already open item 2 (line 334).

## Issues (if FAIL)
None. All four DW items and all six edge cases have evidence in the spec and cross-checks in the code.

**Verdict: PASS**

**All requirements met: YES**
