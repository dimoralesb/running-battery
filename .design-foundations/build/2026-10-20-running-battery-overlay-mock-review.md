# Design Review: Mock - Running Battery overlay (Watch + Details)

## Rendered Evidence (Step 0)
- Screenshots (supplied): `.design-foundations/mocks/running-battery-watch-900.png`, `running-battery-watch-1400.png`, `running-battery-details-900.png`, `running-battery-details-1400.png`. All four are **1440 px wide**; "900" and "1400" are viewport *heights* (above-the-fold and full-page), not widths.
- Extra render by the reviewer (headless Chromium, 390 x 1400, phone width): scratchpad `watch-390.png`, `details-390.png` (not in the project).
- Surface: two greyscale wireframe states of one page. Watch (clip playing, Clips tab open) and Details (clip ended, last frame, Feed tab open with the clip's details).
- No DESIGN.md or JOURNEY.md, so no token or spec contract to check against.

## Assessment B: Deterministic Detector
- Command: `node ~/.claude/plugins/cache/rtd/design-for-ai/4.2.0/scripts/detect.mjs running-battery-watch.html running-battery-details.html > .design-foundations/build/detect.json`
- Exit: 0 (ran, 16 rules)
- Findings: 2. Both are `nested-cards` (high), one per file, on the same element: "`<div class="cell"> is a card inside a card ancestor`" (line 174).
- Opened only after Assessment A findings were frozen: YES (frozen list written to scratchpad before `detect.json` was read)

## Triage
- Baseline (always on): visual (design-dna, checklists, ai-tells CHECKER) and usability (Nielsen 10).
- Dispatched:
  - **data-viz**: the pitch encodes positions, teams and a running path, and the battery gauge encodes one number.
  - **content-design**: real product copy (the moment title, the gauge caption, feed lines, provenance tags).
  - **journey** (light): the Watch to Details state transition and the 19-clip sequence.
- Not applicable: behavioral and deceptive-patterns (no conversion or persuasion mechanics).
- Deferred: none.

## Cross-Pillar Findings (ONE ranked report)

| Severity | Pillar | Problem (in the rendered pixels) | Principle | Fix |
|----------|--------|----------------------------------|-----------|-----|
| Major | usability | In Details, **Previous is disabled at clip 7 / 19**, even though six earlier clips exist. In Watch it was enabled. | Nielsen #3 (user control and freedom); Nielsen #4 (consistency between states) | Keep Previous enabled in Details. Disable it only on clip 1. |
| Major | usability / journey | At 1440 x 900, **the Details payload (Feed tab, stats, feed lines) is entirely below the fold**. The visible change from Watch is a 12 px "Clip ended · last frame" chip plus two restyled buttons. The pitch frame is pixel-identical. | Nielsen #1 (visibility of system status); change blindness at a state transition | Bring the details into view when the clip ends: scroll or anchor to the panel, shrink the pitch, or show a summary strip under the lower third. Make the ended state visible on the pitch itself, e.g. dim the frame. |
| Major | content-design | The stat label reads "**Lost the ball** just after his hardest minutes", which implies he lost it. Feed line 1 says "Marco Tarvsall's **team have lost the ball**". Same fact, two different claims. | Content accuracy and consistency (content-design: one fact, one wording); Nielsen #4 | Use the line's wording for the stat label too, e.g. "His team lost the ball just after his hardest minutes". |
| Major | content-design | Provenance tags expose internal jargon to fans: "Template (plain code)", "Claim 11", and raw citation keys "Ju2022", "Skiba2012, Jones2017". | Nielsen #2 (match between system and real world); content-design plain language | Use viewer-facing labels such as "Estimate" or "From research (Ju et al., 2022)". Keep claim IDs in a tooltip or source view. |
| Major | data-viz | Nothing ties the dark and white markers to the two teams. The score bug has no team swatches, and both placeholder names end in "Albion", which further weakens discrimination. | Direct labelling / every encoding needs a key (data-viz doctrine; Tufte) | Add a colour-chip slot beside each team name in the score bug, even in greyscale. Use distinct placeholder names. |
| Major | visual / usability | The brand mark (top right) is a battery glyph filled to about 70%, on the same screen as the 83% gauge. In a product about one battery number, a second battery reads as a second reading. | Nielsen #4 (consistency); semiotic ambiguity of a data-shaped icon | Make the mark clearly not a reading: empty, outline-only, or a non-battery logotype. |
| Major (unlisted viewport) | visual / responsive | At 390 px wide, the lower third covers about half the pitch. **The gauge and "83%" are clipped off-screen**, and the brand block overflows, which causes horizontal scroll. Not a listed requirement, so it does not block. It would be Critical if phone is in scope. | Responsive reflow (references/visual/responsive.md); Gestalt figure-ground | Below about 700 px, move the lower third under the pitch and stack the gauge under the name. Wrap or hide the tagline. |
| Major | data-viz | The dashed run trace has no direction encoding (no arrowhead, taper or fade). In the static Details frame you cannot tell which way he ran, and the moment ("Caught on the break") depends on that. | Path encoding needs direction (Bertin; data-viz doctrine: honest encoding) | Taper or fade the trace toward its start, or add a small arrowhead at the current position. |
| Minor | detector + visual | Detector `nested-cards` (high): "`<div class="cell"> is a card inside a card ancestor`". **Register-justified:** `.cell` is the battery casing drawing inside the lower third, a graphic, not a card. Assessment A found no card-in-card layout. | ai-tells nested-cards rule; resolved by register (the bordered box is the glyph) | None needed. Optionally render the battery as SVG so the static rule stops matching. |
| Minor | visual | The lower third sits on the bottom touchline (a tangent) and hides the left-flank channel between the box and the touchline. That is the side the hero is running toward. | Composition: tangents and occlusion of content (ch06); figure-ground | Lift it off the touchline or float it below the pitch edge. Plan to move it when the action passes under it. |
| Minor | data-viz | Hero "3" (ringed) and away "3" sit close together near the centre circle. | Discriminability (data-viz); Gestalt similarity | The ring already helps. Consider fading non-hero markers slightly while a clip plays. |
| Minor | content / data-ink | "24:37" appears in both the score bug and the lower third. "83%" appears three times in Details (gauge, stat cell, feed line 3). Stat cell 3 repeats feed line 1. | Tufte data-ink ratio; Nielsen #8 (minimalist design) | Drop the lower-third clock, or the Battery stat cell in Details. |
| Minor | usability | In Details, Replay is filled (primary) and Next is outlined (secondary). In a 19-clip sequence, the strongest call to action goes backward. | Fitts / Hick: the default path should get the strongest affordance; visual hierarchy (ch07) | Make Next the filled button and Replay the outlined one, unless replay really is the expected next action. |
| Minor | journey | The tab named "Feed" holds "this clip's details". Settings is a peer of the content tabs. | Information scent (Pirolli); IA grouping | Rename the tab to "Details" or "This clip", and move Settings out of the content tab row. |
| Minor | visual | In the clip list, the `1fr` player column leaves a gap of about 600 px between the player and the time. Row 5 puts a team in the player column. | Gestalt proximity (ch06) | Pull the time next to the player, or right-align a fixed-width player column. Label team rows consistently. |
| Minor | usability | Watch controls are bare grey text with no button affordance. This is acceptable as "quiet", but the signifiers are weak. | Norman (signifiers); Nielsen #6 | Add a hover/focus outline, or play and pause icons, at low contrast. |

## Distinctiveness (ai-tells CHECKER)
- Direction can be named in a few words: **broadcast sports graphics**. The page uses a boxed all-caps score bug, a lower third on the action, and a single battery-cell gauge as the hero mark.
- The battery-cell gauge with an oversized percentage is a choice a generic dashboard generator would not make.
- Type and colour are declared placeholders, so they are not judged at wireframe fidelity.
- The generic part is the area below the pitch (tabs, table, three-cell stat strip), which is standard dashboard furniture. This is noted, not Critical.
- Result: passes at this fidelity.

## Requirement Fulfillment

### DW-MOCK.1
PREMISE:  the mock renders a viewable surface for the named page(s): a football match overlay in two states, "Watch" (a clip playing) and "Details" (the clip finished, its details in a tab).
EVIDENCE: Both HTML files render in all four supplied 1440-wide screenshots and in the reviewer's 390-wide renders.
- Watch shows the score bug, the pitch with 22 numbered markers, the ball, the ringed hero and the dashed trace, a lower third with the moment, name, position, clock and gauge (83%), the controls Previous / Replay / Pause / Next with 7 / 19, and the Clips tab open with "Now playing" on row 7.
- Details shows the same last frame with a "Clip ended · last frame" chip, Pause disabled, Replay and Next emphasised, and the Feed tab selected with the clip header, three stat cells and three provenance-tagged lines.
VERDICT:  PASS

### DW-MOCK.2
PREMISE:  wireframe structure is sound (this is a greyscale wireframe; colour and type are placeholders). In particular: during Watch, only the score bug, the pitch and the lower third should carry emphasis, with controls and tabs quiet; no boxed all-caps labels outside the score bug; the battery gauge is the one bold graphic.
EVIDENCE:
- **Emphasis in Watch:** The only dark fills or heavy weights are the score bug (2 px border, dark "0–1" block, bold caps), the pitch (mid-grey field with dark home markers and the ringed hero), and the lower third (white panel, 4 px left rule, 24 px bold name, 36 px / 800 "83%").
- **Controls are quiet:** 14 px #616161 text, no borders or fills.
- **Tabs are quiet:** 14 px #616161. Only the selected tab is 600 weight with a 2 px underline.
- **The Clips panel below the fold is subdued:** a grey-shaded current row and bold names in "Fastest so far".
- **No boxed all-caps labels outside the score bug:** Uppercase appears only in `.scorebug`. The "Verified" and "Template" pills, the "Clip ended" chip and the stat cells all use mixed case.
- **The gauge is the boldest graphic:** a 168 x 44 casing with a 3 px stroke, a dark fill and the 36 px / 800 percentage. The small brand mark (26 x 14) is not bold, but see the Major finding on its ambiguity.
- **Structure is otherwise sound at 1440**, with the Major usability and content defects above (none of which these criteria cover).
- **Caveat:** at 390 px the gauge is clipped. Phone is not a listed requirement, so it is reported as Major and non-blocking.
VERDICT:  PASS

**All requirements met:** YES

## Notes (non-blocking)
- **Viewport coverage:** the supplied screenshots are all 1440 px wide. The phone-width defect above comes from the reviewer's own 390 px render. If the overlay must work on phones, treat that row as Critical before build.
- **Wireframe accessibility, not judged as defects at this fidelity:**
  - Tabs are `<a href="#">` with `role="tab"` but no `aria-controls` or `tabpanel`.
  - Pause has no pressed or toggle state.
  - The gauge `role="meter"` has no accessible name.
- **Disabled-button contrast:** disabled buttons (#9e9e9e on white, about 2.7:1) are exempt under WCAG 1.4.3. Fine as is.
- **Small text:** the 12 px captions (gauge caption, tagline, chip) may be small for a TV-distance overlay. That depends on the medium; no requirement covers it.

## Issues (if FAIL)
None blocking. The eight Major findings above should be fixed before the build phase. The disabled Previous button, the stat-label and feed-line contradiction, and the below-the-fold Details payload come first.

**Verdict: PASS**
