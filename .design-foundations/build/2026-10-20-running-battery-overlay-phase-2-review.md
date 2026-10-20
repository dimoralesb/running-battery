# Design Review: Phase 2 - Running Battery overlay, DESIGN.md "Charge Plate" + styled mocks

## Rendered Evidence (Step 0)
- Screenshots read: running-battery-styled-watch-1440.png, -details-1440.png, -watch-light-1440.png, -watch-analyst-1440.png, -watch-390.png (all in `.design-foundations/mocks/`).
- Extra pixels I rendered myself (headless Chromium, scratchpad variants of the analyst mock): battery at 0%, 1%, 99/100% and a narrow 81-83% band, to cover the edge cases the mocks do not show (they only show 83%).
- Pixel sampling of the 1440 PNGs matches the tokens: page `#121312`, plate `#191a19`, score cell `#282b28`, fill and % `#f4f6f2`, name `#e5e9e5`, moment and caption `#b3b9b3`; light page `#fcfdfc` with the same dark plate.
- Computed-style probe on all four HTML files: Saira loaded; `text-transform: uppercase` only inside `.scorebug`; no horizontal overflow; the `:root` token block is byte-identical across the four files (same md5).

## Assessment B - Deterministic Detector
- Command: `node scripts/detect.mjs <the four .html paths> > scratchpad/detect.json`
- Exit: 0 (ran, status "ran", 16 rules)
- Findings: 0
- Opened only after Assessment A findings were frozen: YES (A written to scratchpad/rv/A-frozen.txt first)

## Triage
- Baseline (always-on): visual (design-dna, ai-tells distinctiveness) + usability.
- Dispatched: color and fonts (the requirements are about contrast, tokens, type), data-viz (the battery gauge and the analyst band are a data encoding; the pitch trail is a mark on a data graphic).
- Not applicable: content-design (copy is not under review), journey, behavioral and deceptive-patterns (no conversion surface).
- Deferred: none.

## Cross-Pillar Findings (ONE ranked report)
| Severity | Pillar | Problem (in the rendered pixels) | Principle | Fix |
|----------|--------|----------------------------------|-----------|-----|
| Major (non-blocking, not a listed requirement) | visual / usability | Shirt numbers on the pitch markers are SVG text of 1.35 units: about 10.7 px at 1440 and about 4-5 px at 390 (390 screenshot: they are smudges). Contrast passes (4.80-5.12:1) but the text is below the scale's own floor (`--text-xs` 12 px). | Minimum legible size (ch03); WCAG 1.4.3 is contrast only, so this is a legibility finding, not an AA one | Phone: enlarge marker radius and number, or hide numbers except the ringed player's. Decide before lock. |
| Minor | usability | `.fill { min-width: 2px }` also applies at 0%: my 0% render shows a 2 px sliver, identical to 1%. DESIGN.md says "0% draws no charge (the empty shell shows)". | Nielsen #4 consistency (spec vs UI); truthful encoding (data-viz) | Set the min width only for values > 0. |
| Minor | visual | Analyst mode: the plate's width follows the band label text ("(0-6%)" vs "(94-100%)"): my renders gave plates of about 690, 700 and 750 px. The plate's right edge would jump while the clip plays. | Layout stability; Nielsen #4 | Give `.pct-band` a fixed `min-width` for "(100-100%)". |
| Minor | visual | Three numbers are not tabular: "5.5 m/s (19.8 km/h)" in the Details `dt` label, "83%" inside the feed sentence, "11 more clips". DESIGN.md says every number is tabular. | Tabular figures for numbers (ch03); the spec's own rule | Add `num` to those spans. |
| Minor | data-viz | The lower third covers the oldest (faint) part of the star's run trail (trail runs under the plate at x about 780-880). | Do not occlude data; data-ink | Anchor the plate away from the star, or accept as the faded tail. |
| Minor | visual | Tagline is right-aligned, 12 px, 3 lines with an orphan ("professional"). The ragged left edge hurts scanning. | Ch03 measure and alignment | Left-align inside the right block, or shorten to 2 lines. |
| Minor | design-system | Ball (`#fff`/`#111`) and marker edge `rgba(0,0,0,.5)` are hard-coded and not tokens. The scale (12/14/16/18/22/28/36/48) is not a constant ratio (1.12-1.33), though the doc says "about 1.25". | Token coverage; modular scale (ch03) | Add `--ball`, `--marker-edge`; reword "about 1.25". |
| Note | evidence | `check-contrast.mjs`, cited in DESIGN.md as the evidence script, is not in the repo (it lives in the session scratchpad). The user cannot rerun the 74-pair table. | Reproducible evidence | Commit it under `scripts/`. |

Distinctiveness (ai-tells CHECKER): PASS. The direction is nameable in 3 words: "broadcast charge plate". Choices a generic system would not make: a squared-shell battery as the one bold object, a charge that never takes a status colour, Saira in mixed case with capitals only in the score bug, no cards or shadows, and a muted green-tinted neutral ramp. It is not Inter, not cyan on dark, and has no gradient or glow. The big-number-plus-caption pairing is the "metric hero" template shape, but here it is the product's signature and carries a gauge, so it is register-justified (Minor at most). Pure `#fff` is limited to pitch labels and the trail.

## Requirement Fulfillment

### DW-2.1
PREMISE:  DESIGN.md locked (token block present + user-confirmed). (User confirmation happens after this review; verify the token block is present and complete, and report the confirmation as pending.)
EVIDENCE: DESIGN.md has a full CSS token block: neutrals 1-12 in dark and light (they match a fresh `palette.mjs --seed "#3b7638" --chroma muted --harmony mono` run exactly), semantic aliases, plates, charge, teams (dark and light pairs), pitch, type scale, leading, space, radius, motion. The block is identical in all four mocks. Header status reads "ready to lock - awaiting user confirmation". Gaps are minor (ball and marker edge not tokenised). USER CONFIRMATION: PENDING.
VERDICT:  PASS (token block present and complete; confirmation pending by design)

### DW-2.2
PREMISE:  all text/background pairs pass WCAG AA (>=4.5:1 body, >=3:1 large) in dark and light, verified via `palette.mjs`.
EVIDENCE: The supplied checker reports 74/74 pass. I recomputed pairs with my own WCAG function and sampled the PNG pixels. Dark: `--text` on page 15.18, `--text-secondary` on page 9.32 and on surface 8.73, plate-text-2 on plate 8.73 and on plate-raised 7.17, charge/% on plate 16.05, `--on-team` on home 5.12 and away 4.80. Light: text 13.29, secondary 5.84. Every text size in the render is at least 12 px except the pitch marker numbers (see finding 1; contrast passes). The neutral ramps come straight from palette.mjs and its own light/dark pairs pass in DESIGN.md; the broadcast tokens were checked with the same formula by a separate script (see the Note on `check-contrast.mjs`).
VERDICT:  PASS

### DW-2.3
PREMISE:  interactive elements and the battery fill pass AA non-text (>=3:1) against their background.
EVIDENCE: Charge on plate 16.05, shell/fill on grass 11.65, band brackets `#b3b9b3` on plate 8.73. Outlined Replay/Next edge (`--control-edge`) 9.32 dark and 5.84 light. Focus ring 15.18/13.29. Selected-tab underline 15.18/13.29. Text buttons at rest rely on their text (9.32/5.84). The disabled "Play" (about 2.1:1) is exempt. Team chips on plate 4.80/4.49; markers on grass 3.26-3.48 (away on stripe 3.09, the lowest). Light away dot on the page 3.14 and on surface 3.03, both passing but tight.
VERDICT:  PASS

### DW-2.4
PREMISE:  semantic aliases resolved (`--background`, `--surface`, `--text`, `--accent-solid`) and type scale `--text-xs`...`--text-4xl` present.
EVIDENCE: All four aliases resolve in both themes (`--accent-solid` is deliberately `var(--text)`, not palette.mjs's accent-9, and is documented). `--text-xs` through `--text-4xl` (0.75 to 3 rem) are in `:root` and used by the mock CSS. The supplied checker's last line also confirms they resolve in both themes.
VERDICT:  PASS

### DW-2.5
PREMISE:  no all-caps outside the score bug; numbers use tabular figures.
EVIDENCE: Computed styles on all four files: `text-transform: uppercase` appears only on `.scorebug` and its children, so there is no all-caps anywhere else. The only capitals outside it are abbreviations typed in capitals (FB, WES) and the mock label, which DESIGN.md allows. Tabular is applied (`font-variant-numeric: tabular-nums`) to the score, clock, % (including the band), "7 / 19", shirt numbers, marker numbers, clip numbers and times, m/s lines and Details values. Three numbers are not tabular (the Details `dt` label with "5.5 m/s (19.8 km/h)", "83%" inside a feed sentence, "11 more clips"). None are in aligned columns or animated, so there is no visible effect.
VERDICT:  PARTIAL (the intent is met; three spans need `num` before lock; not a visible violation)

## Edge cases
- **Battery near 0% or 100% stays readable:** HANDLED. Rendered 0%, 1%, 100%: the "0%" and "100%" numbers stay outside the shell and never flip colour, and the shell stays visible. At 100% the charge stops at the 3 px inset, and `.pct` has `min-width: 3.1ch` so "100%" does not jump. Defect: 0% shows a 2 px sliver (Minor, above).
- **The 10-90% band in analyst mode:** HANDLED. At 71-92% the brackets sit 11 px clear of the shell and never cross the charge (`#b3b9b3`, 8.73:1). At 94-100% and 0-6% they hug the edges inside the shell. At 81-83% they narrow to two small ticks with "(81-83%)" still shown. Defect: the plate width varies with the label (Minor, above).
- **Light theme over the green pitch:** HANDLED. The pitch (`#173a1b`/`#1a3e1e`) and plates are the same in both themes, so the markers keep 3.09-3.48:1 on grass. The dark plate on the `#fcfdfc` page is 17.12:1 and the pitch on the page 12.43:1. The light-ground team pair applies only to page dots (4.33/3.14).
- **Contrast of white text on both team colours:** HANDLED BY AVOIDANCE. White fails on all four values (my numbers: home dark 3.64, away dark 3.88, home light 4.42, away light 3.20). The design uses dark `--on-team` (5.12 and 4.80) and the render shows dark numerals on the markers. No white text sits on a team colour anywhere.

**All requirements met:** YES, with DW-2.1 confirmation pending, and DW-2.5 PARTIAL on three non-visible spans (a no-risk fix).

## Notes (non-blocking)
- User confirmation of DESIGN.md is pending, as stated.
- The mocks show only 83%; the 0/1/100/band cases were rendered by me from scratchpad copies, and the mocks themselves were not changed.
- The detector found nothing. It does not read the SVG or the headless render, so it adds no evidence on contrast or legibility.

## Issues (if FAIL)
None blocking. Fix before lock: (1) the three non-tabular numbers; (2) the 0% sliver; (3) the pitch marker numbers on a phone (decision for the user); (4) the plate width in analyst mode.

**Verdict: PASS** (no blocker; DW-2.1 user confirmation pending; DW-2.5 PARTIAL with a trivial fix)
