# JOURNEY.md

<!-- The structural and temporal design spec for the Running Battery overlay (`app/`). Pairs with DESIGN.md (visual tokens; locked 2026-10-20). For visual tokens, see DESIGN.md. Written 2026-10-20, Phase 1 of `.design-foundations/plans/2026-10-20-running-battery-overlay.md`. -->

Scope: the overlay only. Out of scope: the data, the agents' lines, the science, new features. The spec describes today's overlay as it is in the code, then where each part goes in the cleaned-up broadcast.

## Job

**Job story (Klement school; one school only):** When I have a few minutes on my laptop to judge a hackathon entry, I want to see within seconds what it shows and why I can believe it, so I can score it with confidence.

- **Functional job:** see a player's hard running and what it would leave a typical professional, in a clip, then read the evidence behind it.
- **Emotional job:** feel it is a real match broadcast, calm, one thing to look at; never feel told that a player is tired.
- **Social job:** look like a fair judge who checked the sources, not one who took a claim on trust.
- **Second reader:** an analyst (Analyst mode) who wants the 10–90% band and the full citation; a fan (Fan mode, default) who wants the short version.
- **Switch interview (four forces):** NOT CONDUCTED. The push (a dashboard where nothing stands out, user's words 2026-10-20), the pull (a TV graphic with one bold battery), the anxiety (a battery reads as "his state", decision 14) and the habit (judges expect a dashboard) are taken from the brief and the mock review, not from interviews.
- **School note:** Klement job stories only; no Ulwick or Christensen vocabulary.

## Journey

**Actor:** a judge on a laptop (1280–1440 px wide), for the demo video the same screen. **Scenario:** open the site, watch the first clip, understand it, probe it, leave with a verdict. **Scope:** current state (today's overlay) and the signed-off wireframe as the future state. **Owner:** Diego Morales. **Update trigger:** a user sign-off at the Phase 2 mock, and again after the build, before 27 Oct 2026. **Research basis:** UNGROUNDED as to judges' behaviour (no sessions); grounded in the user's brief, the research doc and the mock review. Treat the emotion column as a hypothesis.

| Phase | Actions | Mindset | Emotion | Touchpoints | Opportunity (assigned to) |
|-------|---------|---------|---------|-------------|---------------------------|
| Arrive | Opens the link; the first clip starts at once | "What am I looking at?" | Med | Score bug, brand line, pitch, lower third | One place to look: the pitch and one bar (Phase 2 look) |
| Watch | Follows the star player's run | "Where is it going?" | High | Pitch trail, lower third gauge | Trail shows direction (fix 8) (Phase 2/build) |
| Details | Clip stops; reads the first line and the numbers | "Why is this a moment? Can I trust it?" | High to Med | Details tab: first line, numbers strip, verdict label | First lines visible without scrolling at 1440×900 (fix 1) (build) |
| Probe | Replay; opens sources; Team sheet; Analyst; Next | "Is it only this clip?" | Med | Play bar, Details sources, Team sheet, Settings | Previous and Next always work (fix 2) (build) |
| Leave | Scores; maybe opens Full match | "Did it hold together?" | Med | Full match, the brand line | The brand line says "synthetic match", always visible (signed off 2026-10-20) |

**Decision model:** not a purchase, so the loyalty loop does not apply. The honest model is the explore↔evaluate loop of the messy middle (Google 2020) in small: each clip is a Watch→Details loop, repeated until the judge has seen enough. It is not a funnel (journey-caveats: linear-funnel fallacy).

**Emotion curve (hypothesis):** peak at the first Watch (a clip with one bold battery), a dip if Details is below the fold or a label is jargon ("Template (plain code)"), recovery when a source opens and agrees with the line.

## IA

**Organization scheme:** task (watch, understand, probe) with an exact (chronological) list for clips. **Structure type:** hub-and-spoke on one page: the frame is the hub; the tabs are local spokes, one open at a time (Hick–Hyman 1952: four choices, grouped; Jakob 2000: tabs under media, controls under the picture; Rosenfeld/Morville: global = the frame, local = the tab bar, contextual = the play bar).

```
Overlay (one page, the URL's parameters set where it opens)
├── Frame (always)       score bug · brand · pitch · lower third · play bar · tab bar · footer line
├── Steps (one at a time; the frame stays)
│   ├── Watch       a clip plays once at 1×
│   ├── Details     the clip's last frame, its details open
│   ├── Replay      the clip again at the clip speed (1× unless picked), the details grow
│   └── Full match  the whole match, played or scrubbed
└── Tabs (one at a time, under the frame)
    ├── Clips        the clip list (Highlights) · highlights so far and moments (Full match)
    ├── Team sheet   followed player · both line-ups with batteries · team charts
    ├── Details      this clip's details (Highlights) · the agents' lines as they come (Full match)
    └── Settings     View · Fan/Analyst · Match · Favourite player · Theme · pitch options · Key
```

**Global navigation labels:** Clips, Team sheet, Details, Settings (user sign-off 2026-10-20: the tab that holds a clip's details is named "Details", not "Feed", for scent). **Validation:** NOT VALIDATED (no card sort, no tree test; four labels, one page). The mock review (PASS, 2026-10-20) is the only check.

## Flows

**1. Watch the highlights (task flow).** Entry: the link. Goal: understand one clip. Steps: (1) the first clip plays (Watch, Clips tab) → (2) the clip ends: the Details tab opens with them (Details) → (3) read: numbers, lines, sources → (4) Next → the next clip plays and the viewer gets back the tab they were on. Error: data fails to load (state below). Success: the judge has seen several clips and opened one source.

**2. Auto-play (task flow).** Entry: `auto=1`. Watch → Details (6 s) → next Watch … stops on the last Details. No tab touch needed.

**3. Replay a clip (user flow).** Details → Replay → plays again at the clip speed (1× unless the viewer picked ½× or 2×) with the numbers growing in the Details tab → ends in Details. Decision: Next or Replay again (equal weight).

**4. Follow a player (user flow).** Team sheet tab → click a name → the Full match opens at the current time following him (today's behaviour); in Full match a click only changes who is followed.

**5. Change what I see (user flow).** Settings → Fan/Analyst, Match, Favourite player, Theme, View. Each change shows at once; no Save.

---

## Page specs

### The overlay

**Purpose:** show one player's hard running as one clip at a time, with the battery (what the running would leave a typical professional, never the player's own state) as the one bold graphic, and keep every detail one click away in a tab.

**Entry points:** the site URL with no parameters (opens the first clip, Watch, Clips tab); any deep link in the table below; the demo video's links (`&moment=…`, `&step=details`).

**Content blocks (in order, top to bottom; identical in every step):**

1. **Score bug**, top-left: both team names in full, a team colour chip beside each name, the score, the running match clock. Capitals only here. On phone ≤ 520 px: three-letter codes (WES, RAV) next to the chips; the lower third and tabs still use the full names.
2. **Brand line**, top-right: the battery mark (an outline, never a reading, never a fill level), "Running Battery", next to it, small, "· synthetic match" (`brandSynthetic`; always visible, signed off 2026-10-20), and the tagline "How much hard running each player has done, and the battery expected for a typical pro after the same running" (`tagline`). The name never appears without the tagline (decision 14). On phone the line sits above the score bug and the tagline wraps to two lines.
3. **Pitch**: the mown-stripe pitch with white lines and the two team colours. In a clip: the star player ringed, his run trail (thin path, thick where he ran above 5.5 m/s) with an arrowhead at the current position or a tail fading toward the start (fix 8), his battery icon above him (Fan), the ball, the other markers at normal strength. A pitch flag "Clip ended · last frame" appears top-right in Details only. Height budget below.
4. **Lower third**, docked directly under the pitch at every width (DESIGN.md lock decision 1: inside the pitch it hid a player and the start of his run). Row 1: the moment name and its clock ("Caught on the break · 24:37"). Row 2: shirt number, player name, position. Battery slot: the gauge (outline shell, continuous fill, the 10–90% band as a bracket in Analyst), the percentage, and under the gauge "Expected for a typical pro after the same running" (`ltBatterySub`). Nothing else: no caption, no feed line, no band sentence (decision 5 in the discovery file).
5. **Play bar**, under the pitch (low emphasis): Highlights, a video player's bar (decision 37): on top the clip's progress bar ("Clip time", drag to seek) with "0:12 / 0:53" beside it; under it Previous · Replay · Play/Pause · Next · clip speed ½× 1× 2× (1× by default; the choice carries to the next clip and to Replay; hidden for the whole-match clip, which plays at 120×), then on the right the step name (Watch, Details, Replay) and "7 / 19". Dragging a finished clip back turns Details into Replay at that point, paused; Play in Details plays the Replay. Full match: Play/Pause · match-time slider · speed 1× 5× 20×.
6. **Tab bar**: Clips · Team sheet · Details · Settings. Selected = primary text, weight 600, 2 px underline in the text colour.
7. **Tab panel**: the open tab's content (below).
8. **Footer line**: `disclaimer` ("Synthetic match. The battery is what we expect a typical pro to have left after the same running. It is an estimate and does not show how tired the players actually are.").

**Step × region (what changes; the frame does not):**

| Region | Watch | Details | Replay | Full match |
|--------|-------|---------|--------|------------|
| Pitch | clip plays 1×; star, trail | clip's last frame; trail complete; "Clip ended · last frame" flag | plays at the clip speed; trail grows | whole match; players, ball; focus rings (below) |
| Lower third | moment · player · battery, live | same, at the last frame | same, live | the moment on screen (from 8 s before to 6 s after it) or "Following" the selected player |
| Play bar | progress bar and time; Previous · Replay · Pause · Next · ½× 1× 2× · "Watch" · n / N | same; Play plays the Replay; "Details" | same; "Replay" | Play · slider · 1× 5× 20× |
| Tab that opens | Clips (or the tab the viewer was on) | **Details** | **Details** | **Details** |
| Details tab holds | "This clip's details open when it ends." | the clip's details | the details, growing | the agents' lines as they come |

**Tab rules (one rule set; the viewer's own choice always wins):**

1. A step opens a tab only when the step starts by itself: a clip ending opens the Details tab (step Details), Replay opens the Details tab, a deep link opens its own (table below), Full match from a link opens the Details tab.
2. A tab the viewer clicks is never changed by the app, except rule 3.
3. The Details step borrows the Details tab: if the tab was opened by the clip's end, the next Watch (Next, Previous, a clip row, auto) returns to the tab the viewer was on (Clips if none chosen). If the viewer clicked any tab during Details, that tab stays.
4. Changing View in Settings leaves the viewer in Settings (they are mid-change); the pitch and play bar change at once.

**Pitch and frame height budget (laptop; column width signed off 2026-10-20):** as built, column width = (100vh − 490 px) × 1.514 + 32 px, between 424 and 1180 px, so the lower third fits under the pitch and the first line of the details shows at 1440×900 (column ≈ 653 px; 470 px and 678 px before the clip's progress bar, decision 37); first draft: pitch height = min(frame width ÷ 1.514, 100vh − 330 px), floor 280 px; the frame column is as wide as the pitch and centred (score bug on its left edge, brand on its right, tabs and panel in the same column). At 1440×900: top 72 px, pitch ≤ 570 px (863 px wide), play bar 44, tab bar 48, panel starts at y≈746, about 150 px of panel visible: the first line and the numbers strip. At 1280×720: pitch 390 px, panel starts at y≈568. Fix (1).

---

#### Step: Watch

A clip plays once at 1×, from 3 s before its first run to 2 s after its end (a whole-match clip, "Most ground covered", plays at 120× from kick-off). **What a moment's clip shows (decision 38):** a feed moment measured over minutes gets the part of the match that shows it (`match.json` `clips`, from the export): Caught on the break, from the turnover to the end of the opponents' attack (at least 6 s, at most 15 s); Second wind, his longest high-speed run in the 2 minutes before it; Fresh legs, the substitute's longest high-speed run in his first 10 minutes; the other moments keep 8 s before to 4 s after their second. A moment whose player has no second above 5.5 m/s in its clip gets no clip (Quiet spell and team moments excepted); its lines stay in the full match. **One clip per action:** a moment that shares more than half of the shorter clip with a highlight of the same player becomes that clip's line (one clip, both lines); one that shares more than half of the longer clip with another player's highlight (the same run seen from two players) takes its place. The viewer sees only the score bug, the pitch and the lower third as emphasis (heuristic pass below). The Details tab, if opened by hand, shows "This clip's details open when it ends." (`detailsWait`, new). Previous: the latest clip before this one in match time, disabled only on the first clip; Next: the earliest clip after it, disabled only on the last (fix 2). Play/Pause toggles; Replay jumps to Replay. Clicking a Clips row starts that clip in Watch.

**Exit:** the clip's end (automatic) → Details; Next/Previous/row → another Watch; Settings › View → Full match.

#### Step: Details

The clip stops on its last frame. Lower third unchanged. Pitch flag "Clip ended · last frame". The Details tab opens (rule 1) with, in order:

1. **Numbers strip** (at most 4 cells; Cowan ~4±1): "Top speed in this clip" (m/s, km/h in brackets), "Distance in this clip", "Of it above 5.5 m/s (19.8 km/h)"; a back-to-back clip adds "High-speed run n / N" and "Since his last high-speed run"; a whole-match clip shows "Distance since kick-off" alone. "Speed now" shows only in Replay (it moves). No battery cell: the lower third carries it (no repeated values). **Not built:** the mock's "3rd time so far" cell (no such field in `feed.json`).
2. **The lines**, under "Commentary" (`linesTitle`): the clip's first line (the caption, which for a highlight is the measured caption), then one quiet line (`--text-secondary`, `--text-sm`) saying what this kind of moment is (`about_<kind>`, decision 38; feed moments only; after the first line, which stays above the fold), then the moment's other lines, then, under a quiet "Blocked by the Verifier", any lines the Verifier blocked (struck through with the rule they broke; kept for both modes, they are the Verifier's evidence).
3. **Speed chart** (`speedChart`, hover for values, click to jump; whole-match clip: the distance chart).
4. **"Against the published number"** (`compare`) for highlight clips, once the clip is over.
5. **Team clip** ("Team high-speed running"): instead of 1, 3, 4: the team running chart and that 15-minute block's "High-speed running by situation" chart, after the lines.

**Verdict labels (fix 4).** Fan: each line has one short label, "Verified · measured" (claim "fact"), "Verified · our estimate" (claims 11, 12, 17 and 19c, our model's estimates: the typical-professional line, "the lowest point of his match by our estimate"; decision 39), "Verified · published research" (any other claim); a click opens the claim number and the papers, the measured fields, "Checked by", and the sentence before the Verifier if it was rewritten. Analyst: the full citation open by default ("Claim 11 · Skiba2012, Jones2017", the verdict, the checking stage), and the lower third's band sentence (`ltBand`) as the first analyst line. A highlight's caption (a measured line) reads "Verified · measured" for fans; analysts keep `hlChecked` ("Measured; checked by the Verifier's rules") with its sources. Blocked lines are labelled "Blocked by the Verifier" in both.

**Primary CTA:** Next (equal weight with Replay: both outlined, neutral; the ended state is carried by the pitch flag and the status text, not by a filled button).
**Exit:** Next → next clip, Watch; Replay → Replay; `auto=1` → next Watch after 6 s.

#### Step: Replay

The clip plays again at the clip speed (1× unless the viewer picked ½× or 2×); the lower third's battery moves with it; the Details tab stays open and the numbers, the speed chart and the lines grow with the run ("Speed now" included); "Against the published number" appears when the clip is over. At its end the step becomes Details.

#### Step: Full match

The whole match, paused at load (at `t`, else at the first moment). Same frame. Pitch: all players; **focus rings** only on the followed player, the favourite (dashed ring), and the feed moment's player; hardest-minutes ring (warning colour, always with its Key label), "flat out" pulse and label, battery icons: Fan shows them for the followed and favourite players, or for every outfield player with "Batteries: every outfield player" (Settings). Analyst shows no icons (the Trace is in Team sheet). Lower third: the feed moment on screen (moment name · its clock, its player, his battery; a team moment shows the team slot) or, with none, "Following" · match clock, the followed player and his battery. Play bar: Play/Pause, the match-time slider ("Match time"), speed 1× 5× 20×. The Details tab holds the agents' lines as they come (below). **Exit:** Settings › View → Highlights (restarts the last clip in Watch); Clips tab "Highlights so far" → a clip in Watch; Team sheet name → follow him.

---

#### Tab: Clips

- **Highlights:** "Fastest so far" (`fastest`, one line per team, at the playing time) → a quiet link "Full match" (`viewFull`) → "All the clips, in match order" (`upNext`): one row per clip: number, moment name, player (or the team's full name for a team clip), clock, an 8 px team-colour dot; the playing clip bold on a light neutral row with "Now playing"; click = that clip in Watch. A clip not in the list (a `hl=` clip merged into another) shows as an extra first row "Now playing". The time sits next to the player, not at the far edge.
- **Full match:** "Fastest so far", the quiet link "Highlights", the moment chips (a row of "24:37 Caught on the break", click = jump to 3 s before it in the same view), then the "Highlights so far" panel (`hlTitle`, `hlSub`, "Play highlights" `hlPlay` which starts the reel as `auto=1`, six groups with the top 3 so far each, `hlNone`, `hlAtEnd`).

#### Tab: Team sheet

- **Full match only, at the top:** the followed player's card: "{shirt} {name}, position, team", the battery sentence (`battery`), in Analyst the band (`band`) and `lowChance`, his fastest second so far (`topSpeed`), the hardest-minutes or just-after sentence (`redZone`, `postPeak`), or `offPitch`; "Click a player on the pitch." when none. In Analyst the **Trace** under it: his battery with its band, and his high-speed running in the last minute, on one time axis each.
- **Both steps:** the Batteries sheet (`sheetTitle`, `sheetSub`): two columns by team, each player a row (shirt, name, gauge with percentage; Analyst adds the band mark; a goalkeeper shows "GK" and no gauge; the favourite carries a star; the clip's player is highlighted). Click a name = follow him (in Highlights this opens Full match at the current time, as today).
- **Both steps, below:** "High-speed running per minute" (`teamChart`) and "High-speed running by situation" (`splitChart`, finished 15-minute blocks so far).

#### Tab: Details

- **Highlights:** the Details content above (Watch: `detailsWait`).
- **Full match:** "Live explanations" (heading, newest first), the checkbox "What the Verifier blocked" (with `blocked` and each blocked sentence struck through and its rule), each entry: time button (jumps to 3 s before it and selects the player), team dot, player (or "{team} (team)"), the sentence, verdict label and sources as above; the empty state; "{n} more later in the match."

#### Tab: Settings

In this order, applied at once, no Save: **View** (Highlights | Full match), **Audience** (Fan | Analyst), **Match** (the two matches' names), **Favourite player** (grouped by team, with shirt numbers, and a "none" option), **Theme** (Dark | Light; dark by default, not stored), then **On the pitch**: "Batteries: selected and favourite (tick for all)" (Fan, Full match) and **Key** (a fold-out: the focus ring, hardest minutes, flat out, the faded player (`legendGap`, decision 38), battery, favourite).

---

### Layouts

| | Laptop 1280–1440 px | Phone 360 / 390 px (no sideways scroll) |
|---|---|---|
| Frame | one centred column the width of the pitch (budget above) | one full-width column, 16 px gutters |
| Score bug / brand | bug left, brand right, one row | brand line above; bug with codes (WES, RAV) and chips; the clock stays |
| Lower third | under the pitch, full column width | under the pitch; rows stacked; gauge and percentage always visible (gauge under the name, not beside it) |
| Analyst band | bracket on the gauge and "(71–92%)" beside the percentage, same row; no second row | the same, on the gauge's row; the band sentence is in the Details tab and the gauge's spoken name |
| Play bar | one row | one row of four 44 px buttons; step name and "n / N" on a second line |
| Tabs | four text tabs | four tabs sharing the width (≈ 260 px of text at 14 px) |
| Panels | lists and 2-column sheets | one column; Team sheet one column; charts scale to the width; numbers strip 2 across; Settings stacked |

Breakpoints: bug codes at ≤ 520 px (as today); lower third moves under the pitch at ≤ 700 px; panels single column at ≤ 600 px.

### States

- **Default:** as above, Fan mode, dark, first clip, Watch, Clips.
- **Loading:** "Loading the match…" in place of the frame. **Error:** "Could not load the match: …" with the reason; the page stays usable (Settings › Match is out of reach, so the line says to reload).
- **No clips** (a match whose feed has no shown lines): opens as Full match.
- **Empty Details tab (Full match start):** "The first explanation comes with the first moment. Press play or pick a moment."
- **Player not on the pitch** (before kick-off, after a substitution): the battery slot shows `offPitch`, no gauge.
- **Success:** the clip's end with its details visible (Details).

### Edge cases (from the plan)

- **A team clip** (no player): no battery and no empty gauge. The battery slot shows both teams' running: each team's full name with its team-colour chip and its metres per minute above 5.5 m/s in play, from the latest finished 5-minute block, under `teamChartAxis` ("m per minute in play"); before the first block, `hlNone`. The star-player dimming is off: no marker is dimmed when there is no star.
- **A goalkeeper** (Full match: followed from the Team sheet; no goalkeeper clip exists in either match today): the lower third shows the position "GK" and no gauge, no percentage, no empty shell; no battery icon on the pitch.
- **A clip merged into another** (`reel()` drops overlapping clips; `hl=` can still name one): it plays as a one-off, appears as the extra first Clips row, has no "n / N", and Previous/Next still work by match time.
- **`step=details`:** opens the Details tab, paused on the last frame. **`auto=1`:** needs no tab touch (tab rules 1 and 3).
- **Analyst on a phone:** no second row (Layouts).
- **Switching Fan/Analyst or Match mid-clip:** the clip keeps playing; the list, lines and band follow the new mode; the count disappears if the clip is no longer in the list.

---

### Heuristic pass: emphasis during Watch (DW-1.4)

Doctrine: Nielsen #8 (nothing irrelevant competes), Von Restorff (the one thing that differs is remembered), Fitts and Jakob (play controls under the picture, small and where the cursor rests).

| Region | Role in Watch | Emphasis | Colour |
|--------|---------------|----------|--------|
| Score bug | carries emphasis | solid block, capitals, heavy score numeral | neutral dark block; the only colour is the two team chips |
| Pitch | carries emphasis | star player ringed, thick run trail, battery icon; every other marker at normal weight | team colours on grass |
| Lower third | carries emphasis | bold name; the gauge and percentage are the one bold graphic | the gauge fill is the only saturated element outside the team colours |
| Brand line | quiet | small outline mark, secondary text | none |
| **Play bar** | **quiet** | text buttons, 14 px regular, secondary text colour, no fill, no border at rest; hover: primary text and underline; keyboard focus: a 2 px ring, on focus only | **none** |
| Status and "n / N" | quiet | secondary text | none |
| **Tab bar** | **quiet** | secondary text; the selected tab in primary text, weight 600, 2 px underline in the **text** colour (not a team colour, not an accent) | **none** |
| Clips panel | quiet | regular rows; the playing row on a light neutral fill, weight 600 | the only colour is the 8 px team dot |
| Footer line | quiet | small secondary text | none |

Checks against the signed-off wireframe: `.controls` and `.tabs a` use `--text-secondary` with no fill and no border; the Watch file has no filled control (`class="emph"` appears 0 times in `running-battery-watch.html`; it appears only in the Details file, and the Details spec above removes it by making Replay and Next equal); in `running-battery-watch-1400.png` the heaviest marks are the score bug, the ringed player with his trail, and the lower third's 83% and gauge. Details step: Replay and Next outlined, equal weight; no saturated fill on any control.
Dropped to meet this: the red "● Watch" dot of today's step chip (saturated colour on a status), and the filled, accent-underlined "ready" buttons of today's Details (`.replay-btn.ready`, `.next.ready`).

---

### Element map: today's overlay → the new place (DW-1.2)

Frame = always visible. Tabs: C Clips, T Team sheet, D Details, S Settings. "Kept" = same content, new place; "Dropped" has a reason.

| Today (file) | Goes to | Note |
|--------------|---------|------|
| Brand "Running Battery" (`App.tsx` `.brand`) | Frame, brand line | outline mark added; never a reading |
| Tagline `tagline` | Frame, brand line | stays with the name (decision 14) |
| View toggle Highlights / Full match | S › View; also a quiet link in C | |
| Match select (`match_story`, `match_natural`) | S › Match | |
| Fan / Analyst toggle | S › Audience | |
| Favourite player select | S › Favourite player | |
| Theme (URL only today) | S › Theme | the plan's Settings item; dark default |
| Score bug (names, score, clock, phone codes) | Frame | chips added (fix 5) |
| "Fastest so far" ×2 (`fastest`, `.fastest-strip`) | C, top | |
| Clip count "n / N" | Frame, play bar | |
| Clip heading (name · clock · who) | Frame, lower third rows 1–2 | |
| Step chip (Watch / Details / Replay; `.step-chip`) | Frame, play-bar status text | red dot **dropped**: saturated colour on a quiet control |
| Pitch: grass, stripes, lines, ball, markers, shirt numbers, team colours | Frame, pitch | kept as is |
| Pitch: selected-marker outline, marker click | Frame, pitch | kept; in a clip it only outlines |
| Pitch: clip trail, thick high-speed runs, value label at the end | Frame, pitch | direction added (fix 8) |
| Pitch: reach circles | **Removed** (decision 37) | at 1 s their size is fixed, so they told a first-time viewer little |
| Pitch: battery icon above a player | Frame, pitch | Fan only; clip's player / followed / favourite / all |
| Pitch: focus ring, hardest-minutes ring, flat-out pulse + label, favourite ring (Full match) | Frame, pitch | explained in S › Key |
| Pitch: dimming of non-star markers | Frame, pitch | kept for player clips; **dropped** for team clips (it dims everything) |
| (new) "Clip ended · last frame" flag | Frame, pitch, Details | fix of the mock review (change blindness) |
| Lower third: moment tag (`LowerThird` `.lt-tag`) | Frame, lower third row 1 | team-colour block **dropped** (Phase 2: no boxed labels) |
| Lower third: shirt, name, position | Frame, lower third row 2 | |
| Lower third: clock | Frame, lower third row 1 | one clock only, with the moment name |
| Lower third: "Battery" label (`ltBattery`) | **Dropped as visible text** | `ltBatterySub` carries it; kept as the gauge's spoken name |
| Lower third: gauge + band bracket + percentage | Frame, lower third | the one bold graphic |
| Lower third: "Expected for a typical pro after the same running" (`ltBatterySub`) | Frame, lower third | |
| Lower third: caption row (the clip's line / feed moment's sentence) | D, first line of Details; Full match: D, live list | moved off the picture (the brief) |
| Lower third: band sentence (`ltBand`) | D, first analyst line; gauge's spoken name | no second row |
| Lower third: team clip (no battery) | Frame, lower third, team slot | both teams' running (edge cases) |
| Lower third: goalkeeper / off pitch | Frame, lower third | "GK", or `offPitch` |
| Lower third: "Following" (`ltFollow`), Full match | Frame, lower third | |
| Previous / Replay / Play-Pause / Next | Frame, play bar | quiet; Previous by match time; Play disabled in Details |
| "Ready" emphasis on Replay and Next in Details | **Dropped** | equal weight, outlined |
| Team sheet in the left column (`TeamSheet`, `sheetTitle`, `sheetSub`) | T | |
| "All the clips, in match order" (`upNext`, `.up-next`) | C, Highlights list | |
| Replay panel: numbers (`Stats`, `stat*`) | D, numbers strip | |
| Replay panel: speed / distance chart (`SpeedChart`) | D | |
| Replay panel: "Against the published number" (`Compare`) | D | |
| Replay panel: "Commentary" + lines (`Line`, `hlChecked`) | D, the lines | |
| Replay panel: blocked lines with their rule | D, under the lines | both modes |
| Team clip: `TeamChart` + block `SplitChart` in the Replay column | D (team clip Details) | |
| Full match: transport (play, slider, 1× 5× 20×) | Frame, play bar | |
| Full match: Key (`Legend`, `key`, `legend*`) | S › Key | |
| Full match: "Batteries: selected and favourite / every outfield player" checkbox | S › On the pitch | Fan, Full match |
| Full match: moment chips | C (Full match) | headless row kept |
| Full match: Highlights panel (`Highlights.tsx`: `hlTitle`, `hlSub`, `hlPlay`, six kinds, `hlNone`, `hlAtEnd`) | C (Full match) | |
| Full match: player card (`.player-card`: `battery`, `band`, `lowChance`, `topSpeed`, `redZone`, `postPeak`, `offPitch`) | T, top | |
| Full match: `Trace` (battery with band; high-speed running; Analyst) | T, under the card | |
| Full match: `TeamChart` ("High-speed running per minute") | T, below the sheet | |
| Full match: `SplitChart` ("High-speed running by situation") | T, below the team chart | |
| Chart furniture in every chart (axes, grid, hover crosshair and tooltip, "Hover for values; click to jump there", the dashed 5.5 m/s line, shaded high-speed runs and hardest-minutes zones, the half-time line, direct end labels, team swatch legend, the split's per-situation bars and share line) | Goes with its chart (D or T) | kept; tooltips follow the `traceTip` correction |
| Full match: Feed (`Feed.tsx`: heading, entries, time button, team dot, verdict badge, `Sources`, "n more later") | D | labels by audience (fix 4) |
| Full match: "What the Verifier blocked" checkbox, `blocked`, blocked list | D | |
| Full match: empty-feed sentence | D | |
| Footer `disclaimer` | Frame, footer line | |
| "Loading the match…", "Could not load the match" | States | |
| Unused code: `.hl-caption`, `.clip-caption`, `Highlights` props `active` and `reelOn` | **Dropped** | not rendered today |

---

### Deep links (DW-1.3)

The app reads the URL once at load and never writes it. Precedence for the clip: `hl` > `moment` > `item` > the first clip. Unknown or missing values fall back to the default (never an error).

| Parameter | Values (default) | What it sets | Screen · tab it opens |
|-----------|------------------|--------------|------------------------|
| `view` | `full`, else Highlights | the step | `full` → Full match · **Details**, paused; else Highlights → Watch · **Clips** |
| `match` | `story` (first), `natural` | the data set (S › Match) | same screen; an unknown id shows the load error |
| `t` | seconds from kick-off, > 0 | Full match: the time it opens at (without `t`: the first moment's time, not 0). Highlights: the start time inside the clip (for capture; a time outside the clip is not supported) | Full match · Details; Highlights unchanged |
| `mode` | `analyst`, else Fan | S › Audience; the clip list (a clip needs a line shown in that mode), band, lines, citations | the screen the other parameters give |
| `player` | a player id, e.g. `H04` | Full match: the followed player (T card, "Following"). Highlights: with `moment`, narrows to his clip; the clip's own player then wins | Full match · Details (card in T); Highlights per its step |
| `favourite` | a player id (the feed's favourite) | S › Favourite player; ring, star, highlighted lines | no tab change |
| `theme` | `light`, `dark` (dark) | S › Theme | no tab change |
| `batteries` | `all` | Full match, Fan: icons on every outfield player (S › On the pitch); ignored in Highlights | Full match · Details |
| `hl` | `top_speed`, `longest_run`, `recovery_run`, `back_to_back`, `busiest_minute`, `most_ground` | the match's best highlight of that kind (whole match, not "so far"); ignored with `view=full` | Highlights · Watch · Clips (per `step`) |
| `moment` | a moment kind (first in the list) or a full moment id; `&player=` narrows | that feed moment's clip; none found → the first clip | Highlights, as `hl` |
| `item` | n ≥ 1, in the current mode's list (numbers shift with `mode`) | the n-th clip | Highlights, as `hl` |
| `step` | `watch` (default), `details`, `replay` | with a clip: plays at 1×; stops on its last frame with its details; plays it again at the clip speed with the details growing | `watch` → **Clips**; `details` → **Details**, paused; `replay` → **Details**. Ignored in Full match |
| `auto` | `1` | the clips play one after another: Watch → Details (6 s) → next Watch …; stops after the last Details, or on entering Full match or following a player from T | Highlights; Clips during Watch, the Details tab during the Details step, no touch needed. With `view=full` it waits until the viewer enters Highlights |

Not in the URL: the open tab, speed, the blocked-lines checkbox, marker clicks.

---

### New copy, to verify (words: plain English in football's words; m/s then km/h; teams in full; never "tired"; the battery always says it is what the running would leave a typical professional)

| Key (proposed) | Text | Where |
|----------------|------|-------|
| `brand` | Running Battery | brand line (hard-coded today) |
| `brandSynthetic` | synthetic match | brand line, next to the name (signed off 2026-10-20) |
| `tabClips` `tabTeam` `tabDetails` `tabSettings` | Clips · Team sheet · Details · Settings | tab bar |
| `settingsView` `settingsAudience` `settingsMatch` `settingsFavourite` `settingsTheme` `settingsPitch` | View · Audience · Match · Favourite player · Theme · On the pitch | Settings |
| `themeDark` `themeLight` | Dark · Light | Settings |
| `nowPlaying` | Now playing | Clips row |
| `clipEnded` | Clip ended · last frame | pitch flag, Details |
| `detailsWait` | This clip's details open when it ends. | Details tab during Watch |
| `verdictMeasured` | Verified · measured | verdict label |
| `verdictEstimate` | Verified · our estimate | verdict label (claims 11, 12, 17, 19c) |
| `verdictResearch` | Verified · published research | verdict label |
| `verdictBlocked` | Blocked by the Verifier | verdict label |
| `papers` | Papers | opened source |
| `traceTip` | Battery expected for a typical pro: {pct}% ({lo}–{hi}%) | Trace tooltip, replaces "battery {pct}%" |

**Existing text to move into `copy.json` so the Verifier sees it** (today hard-coded): "Fan", "Analyst", "Favourite player…", "Play", "Pause", "Match time", "Loading the match…", "Could not load the match", "Click a player on the pitch.", the pitch's aria-label, "Live explanations", "What the Verifier blocked", "Nothing blocked so far.", the empty-feed sentence, "{n} more later in the match.", "(team)", "Measured fact", "Claim {n}", "Checked by", "Before the Verifier", "Rewritten by the Verifier", the Trace and chart hints and tooltips ("typical-pro chance" becomes `lowChance`'s wording).

---

### Signed off (user, 2026-10-20)

1. **Frame width on laptop:** the whole column narrows to the pitch's width (≈ 860 px at 1440×900) so the tabs and the first lines of details show without scrolling; every player stays visible.
2. **Tab "Details"** (not "Feed") holds this clip's details during the Details step; in the full match the same tab lists the agents' lines as they come. Tabs: Clips · Team sheet · Details · Settings.
3. **A quiet "Full match" link in Clips**, besides Settings › View. Stands.
4. **"Synthetic match" in the brand line**, small, next to the name ("Running Battery · synthetic match"), always visible; the footer line keeps `disclaimer`.
5. **Tab borrow rule** (the Details step borrows the Details tab, the next Watch hands the tab back). Stands.
6. **Dark by default** even when the device is set to light. Stands.
7. **The mock's "3rd time so far" cell is not built** (no data field). Stands.
