# Discovery + Design: Phase 1 - Screen spec

Plan: `.design-foundations/plans/2026-10-20-running-battery-overlay.md` · Branch `redesign` · Doctrine read: journey (`references/journey/journey.md` + `journey-stack.md` + `journey-caveats.md`), usability (`skills/usability/SKILL.md` + `usability-principles.md`).

## Artifacts Found / Current State

- No `DESIGN.md`, no `JOURNEY.md` at the project root. Phase 1 creates `JOURNEY.md`; DESIGN.md is Phase 2.
- Approved wireframe states (Watch, Details) in `.design-foundations/mocks/` (HTML + 900/1400 PNGs); mock review in `.design-foundations/build/2026-10-20-running-battery-overlay-mock-review.md` (PASS, eight Major findings carried into this phase).
- Today's overlay read in full: `App.tsx` (478 lines), `Highlights.tsx`, `Replay.tsx`, `Battery.tsx`, `Pitch.tsx`, `Feed.tsx`, `Trace.tsx`, `TeamChart.tsx`, `SplitChart.tsx`, `data.ts`, `styles.css`, `copy.json` (100 keys + `_note`). Screenshots `hl.png`, `full.png`, `phone.png` are older than the code (they still say "Second Wind", show the right-hand "All the clips" column and a "Details" chip on the phone); the code wins where they differ.
- Feed data checked for the edge cases: 13 moments in the story match, 14 in the natural one; **team moments** (no player) exist ("Who's doing the running", 3 in the story match); **no goalkeeper clip** exists in either match, but a goalkeeper can still be followed in Full match through the Team sheet.

## Gaps (found while mapping today's overlay)

1. **The mock's third stat cell has no data.** "Lost the ball just after his hardest minutes: 3rd time so far" is not a field in `feed.json` (the count lives only inside the sentence "This is the third time ..."). Building it would be a data change (OUT of scope). Spec drops the cell; the feed line already carries the words fix (3) asks for ("his team lost the ball").
2. **Hard-coded English outside `copy.json`** (so outside the Verifier's copy test): `App.tsx` (brand name, "Fan", "Analyst", "Favourite player…", "Pause", "Play", "Loading the match…", "Could not load the match", "Click a player on the pitch.", the pitch's aria-label), `Feed.tsx` (the six verdict labels, "Measured fact", "Claim n", "Checked by", "Before the Verifier", "Live explanations", "What the Verifier blocked", "Nothing blocked so far.", the empty-feed sentence, "n more later in the match.", "(team)"), `Replay.tsx` ("Measured · …", "LLM check", "Rule"), `Trace.tsx` (tooltip and hint), `TeamChart.tsx` and `SplitChart.tsx` (tooltips, "min", "m a minute"). Listed in JOURNEY.md as "text to move into copy.json" so the build puts them through the Verifier.
3. **`Trace.tsx` tooltip says "battery 63%" and "typical-pro chance 12%"**: "battery 63%" without "typical professional" reads as the player's own state (decision 14). Spec corrects it (new copy `traceTip`).
4. **Previous is computed from the clip's index in the list** (`prev = ix > 0 ? items[ix-1]`), so it is disabled whenever the playing clip is not in the list (a deep link `hl=` clip merged away, or Fan/Analyst switched mid-clip) and the "n / N" count is blank. Mock-review Major #2 saw it disabled at clip 7 / 19. Spec: Previous and Next follow match time (latest clip before, earliest clip after), not list position.
5. **A team clip dims every marker** (`dim = !star && ...` is true for all when `clip.player` is null), so the pitch is washed out. Spec: no dimming when the clip has no player.
6. **`view=full` with `auto=1`, `t` with a clip, and the "Highlights" view flag when there are no clips** are quirks of today's URL handling, listed in the deep-link table so the build keeps (or knowingly changes) them.
7. **Tab label "Feed" holds "this clip's details"** during Details (mock-review minor). The plan fixes the four tab names; kept, and raised as an open question for the user.
8. **The mock's play bar and tab panel at 1440×900:** tab bar sat at y≈944, below the fold (fix 1). Height budget for the shorter pitch is worked out in the spec (pitch height ≤ 100vh − 330 px).

## Gate Status

- DESIGN.md: absent (not needed for Phase 1; Phase 2 establishes and locks it). JOURNEY.md: produced here. Prerequisites for Phase 1: research doc present, mock signed off. **Met.**
- Gate 1 (Design page laid out before JOURNEY.md page specs exist → stop): this phase is the one that produces the page specs; nothing styled is produced here.

## DW Verification

| DW-ID | Done-When Item | Status | Evidence |
|-------|---------------|--------|----------|
| DW-1.1 | JOURNEY.md `## Page specs` has a complete entry for the overlay covering Watch, Details, Replay and Full match | COVERED | Read-through of the entry against the page-spec template (purpose, entry points, content blocks, states, primary CTA, exit) plus a step × region table with all four steps and four tabs; scripted check that the four step names and four tab names each have their own subsection |
| DW-1.2 | every element of today's overlay is mapped to a place (frame or a named tab) or listed as dropped with a reason | COVERED | Element map table in JOURNEY.md, built from the source (every component and every `className` region); scripted cross-check: all 100 `copy.json` keys appear in this file's copy ledger with a destination; every component file named in the map |
| DW-1.3 | every current deep link maps to the screen and tab it opens | COVERED | Deep-link table in JOURNEY.md: all 13 parameters from `App.tsx` (`view match t mode player favourite theme batteries hl moment item step auto`), with defaults, precedence and quirks; scripted check that each parameter name appears in the table and that every `QUERY.get(...)` in `App.tsx` is listed |
| DW-1.4 | heuristic pass: during Watch only the score bug, pitch and lower third carry emphasis; play controls and tab bar stay quiet (low emphasis, no saturated colour) | COVERED | Watch emphasis table in JOURNEY.md checked against the approved wireframe: `running-battery-watch.html` CSS (`.controls` and `.tabs a` use `--text-secondary`, no fill, no border; `.emph` classes appear in the Details file only: grep count 0 in the Watch file) and `running-battery-watch-1400.png`; Nielsen #8 and Von Restorff cited |

**All items COVERED:** YES. DW-IDs in this table: 4. DW-IDs in the dispatch prompt: 4.

## Design Decisions

Each is stated in JOURNEY.md with its source.

1. **One frame, four steps, four tabs.** The frame (score bug, brand, pitch, lower third, play bar, tab bar) never changes between steps; only the pitch's content, the play bar's buttons, and the tab panel change. Hick–Hyman 1952 (four tabs, one open at a time); Jakob 2000 (tabs under media, play controls under the picture).
2. **Which tab opens when.** Details, Replay and Full match open **Feed**; a hand-picked tab is never overridden; Details "borrows" Feed and the next Watch hands the viewer back the tab they were on (Clips by default). Nielsen #1 (the clip's end is visible in the panel) and #3 (the viewer's own choice wins). `auto=1` therefore needs no tab touch.
3. **Pitch height budget.** At 1440×900: top 72 px, pitch ≤ 570 px, play bar 44, tab bar 48, so the panel starts at y≈746 and ~150 px of details (first line and the numbers strip) show. Rule: pitch height = min(width ÷ 1.514, 100vh − 330 px), floor 280 px; the whole frame column takes the pitch's width and is centred. Nielsen #1; change-blindness finding in the mock review.
4. **Previous and Next follow match time.** Gap 4. Nielsen #3 and #4.
5. **The lower third carries three things only:** the moment (with its clock), the player, the battery (gauge, percentage, the "typical professional" line). No caption, no feed line, no band sentence in it. Nielsen #8; the brief ("no feed lines during playback"). The caption becomes the first line of Details.
6. **Analyst band in the lower third without a second row:** the band is a bracket on the gauge plus "(lo–hi%)" beside the percentage in the same row; the full band sentence moves to the first analyst line of Details and to the gauge's accessible name. Satisfies the plan's phone edge case.
7. **Team clip lower third:** both teams' running (latest finished 5-minute block, `m per minute in play`, two team-coloured figures) in the battery slot; no gauge. Reuses `teamChartAxis`.
8. **Verdict labels by audience.** Fans: "Verified · measured | published research | our estimate" from the entry's claim (fact → measured; claim 11 → our estimate; any other claim → published research), click opens claim and papers; analysts: today's full citation, open by default. Fix (4); Nielsen #2.
9. **Team charts live in the Team sheet tab** (the people and the teams), the followed-player card and the analyst Trace at the top of it in Full match. Keeps Feed to one job (the lines) and every current feature reachable.
10. **Settings holds View, Fan/Analyst, Match, Favourite player, Theme, then the pitch options and the Key.** Dark is the default; Light is chosen here or by `?theme=`; session-only, no storage. Hick's law: grouped, not a 7-control row.
11. **Emphasis budget in Watch:** three carriers (score bug, pitch with the star player's ring and trail, lower third with the gauge as the only bold graphic); controls and tabs are secondary text, no fill, no saturated colour. Von Restorff 1933 (isolation: one thing differs), Nielsen #8.
12. **No new data and no new features.** The only additions are labels and affordances the sign-off asked for; each is in the "new copy, to verify" list.

## Recommendation

**BUILD.** All four DW items are coverable; no DESIGN.md lock is in play; no scope conflict.

---

## Production notes and validation (filled after production)

See the end of this file (section "Validation results").

## Copy ledger (DW-1.2 cross-check)

Every key of `app/src/copy.json` with where it goes (F = frame, C/T/Fd/S = Clips / Team sheet / Feed / Settings tab, D = Details block, L = lower third, K = kept key, x = not shown as text).

- Frame: `tagline` (F brand), `disclaimer` (F footer), `stepWatch` `stepDetails` `stepReplay` (F play-bar status), `prev` `next` `replayButton` (F play bar), `ltBatterySub` (F lower third), `ltFollow` (F lower third, Full match), `reachLabel` (F pitch label), `flatLabel` (F pitch label, Full match), `offPitch` (F lower third / T player card).
- `ltBattery` (x: dropped as visible text, the sub-line and the gauge carry the brand; kept as the gauge's spoken name).
- Clips tab: `upNext` (C list heading), `fastest` (C top), `hlTitle` `hlSub` `hlPlay` `hlStop` `hlNone` `hlAtEnd` (C, Full match), `hl_top_speed` `hl_longest_run` `hl_back_to_back` `hl_busiest_minute` `hl_most_ground` `hl_recovery_run` (C and L moment names), `viewHighlights` `viewFull` (S View, and the C shortcut link).
- Moment names: `kind_red_zone` `kind_exposed_on_turnover` `kind_second_wind` `kind_fresh_legs` `kind_not_tired_tactical` `kind_tug_of_war` `kind_flat_out` (C rows, L moment line).
- Team sheet tab: `sheetTitle` `sheetSub` (T), `battery` (T player card, gauge spoken name), `band` (T player card, analyst), `lowChance` (T player card, analyst), `topSpeed` (T player card), `redZone` `postPeak` (T player card), `teamChart` `teamChartSub` `teamChartAxis` (T team charts; `teamChartAxis` also the team-clip lower-third unit), `splitChart` `splitChartSub` `splitSoFar` `splitBlock` `splitAxis` `splitShare` `splitHover` `sit_after_losing` `sit_after_winning` `sit_on_ball` `sit_off_ball_high` `sit_off_ball_deep` (T and Fd for team clips), `traceBattery` `traceBatteryAxis` `traceHsr` `traceHsrAxis` (T analyst Trace), `ltBand` (analyst line, first line of D and the gauge's name).
- Feed tab (Details and Full match): `linesTitle` `hlChecked` (D lines), `blocked` (Fd, Full match "What the Verifier blocked"), `statSpeedNow` `statTop` `statDistance` `statHsr` `statDistanceMatch` `statRun` `statGap` (D numbers strip), `speedChart` `speedChartSub` `speedAxis` `distanceChart` `distanceChartSub` `distanceAxis` `chartHint` (D speed chart), `compare` `cmpTopSpeed` `cmpRun` `cmpGap` `cmpMinute` `cmpGround` (D compare).
- Settings tab: `match_story` `match_natural` (S Match), `key` `legendFocus` `legendRedZone` `legendFavourite` `legendBattery` `legendFlatOut` `legendReach` (S Key; `legendReach` also the first-lines note of a reach clip's Details), `batteriesSome` `batteriesAll` (S pitch option).
- `_note` is a file comment, not on screen.

## Validation results

(appended below after production)

### Results (2026-10-20, after production)

| DW-ID | Result | Evidence |
|-------|--------|----------|
| DW-1.1 | PASS | Scripted check on `JOURNEY.md`: `## Page specs`, Purpose, Entry points, Content blocks, States, Primary CTA, Exit all present; subsections "Step: Watch / Details / Replay / Full match" and "Tab: Clips / Team sheet / Feed / Settings" all present; a step × region table covers the four steps |
| DW-1.2 | PASS | 99 of 99 `copy.json` keys (excluding `_note`) appear in the copy ledger above with a destination (0 missing); the element map has one row per component region of `App.tsx`, `Highlights.tsx`, `Replay.tsx`, `Battery.tsx`, `Pitch.tsx`, `Feed.tsx`, `Trace.tsx`, `TeamChart.tsx`, `SplitChart.tsx`; the class list of all `.tsx` files (135 distinct class names) was walked against it and the chart furniture row added; 6 items are dropped, each with a reason in its row (red Watch dot, "ready" button emphasis, `ltBattery` as visible text, team-clip dimming, team-colour moment tag block, unused `.hl-caption` / `.clip-caption` / `active` / `reelOn`) |
| DW-1.3 | PASS | `grep QUERY.get` in `App.tsx` finds 13 parameters (`auto batteries favourite hl item match mode moment player step t theme view`); all 13 have a row in the deep-link table, each with its screen and tab; precedence (`hl` > `moment` > `item` > first clip) and defaults read from `itemFromUrl` and the load effect |
| DW-1.4 | PASS | Watch emphasis table (three carriers; play bar and tab bar quiet, no saturated colour). Wireframe evidence: `running-battery-watch.html` `.controls` colour `var(--text-secondary)`, no fill; `.tabs a` the same, selected tab weight 600 with a 2 px underline in `var(--text)`; `class="emph"` count in the Watch file = 0, in the Details file = 2 (removed by the spec: Replay and Next equal); `running-battery-watch-1400.png` read by eye: heaviest marks are the score bug, the ringed player with his trail, and the lower third's gauge and 83% |

Other checks: word rules grep on `JOURNEY.md` (`spell`, `pressing`, `tired`): `tired` appears three times, all in rule statements or the quoted existing disclaimer; no "spell", no "pressing". Pitch budget recomputed: 1440×900 → 72 + 570 + 44 + 48 = 734, panel from 746, about 150 px visible; 1280×720 → 72 + 390 + 44 + 48 = 554, panel from 566.

Not done in this phase (by design): no `palette.mjs` run (no colour tokens here, Phase 2), no `prototype` render (the wireframe was signed off; the styled mock follows DESIGN.md). Browser MCP not needed.

Open items for the user are listed at the end of `JOURNEY.md`; the project's `CLAUDE.md` `## Design Context` line `- **Journey spec**: JOURNEY.md` was not added (the dispatch forbids touching other files); the parent should add it.
