# Design: Charge Plate

**Date:** 2026-10-20 · **Status:** **locked** — confirmed by the user on 2026-10-20, with the three changes under "Lock decisions" at the end
**Archetype:** broadcast sports graphics · **Register:** calm structure · expressive at: the lower third's battery (one moment, full amplitude)
**Grounding:** a TV channel's on-screen graphics (one dark plate at a time over the picture, capitals only in the score bug) + a phone's battery indicator (a squared shell, a charge that fills it, the number beside it)
**DNA:** Cinematic Dark, borrowed type voice (a squared sports sans in mixed case) · **Dominant axis:** the battery (shape, not colour)
**Composition:** `cinematic-dark × frieze-bands` (dealer, variance 4, seed `running-battery|2026-10-20|0|pin:chroma=muted,discipline=frieze-bands,family=cinematic-dark,hue=143`): stacked bands, each its own ground with hard edges: score bug row, pitch, play bar, tab bar, panel. `monolith-center` was refused by the dealer as a tell cell.
**Pins:** family (broadcast, dark default), hue (the pitch green), chroma muted, the layout (JOURNEY.md, signed-off wireframe), the team colours and pitch, the signature (the battery is the brand: the user's own move, replacing the dealt `exposed-grid`).

Pairs with JOURNEY.md (structure: what is on screen in each step). This file is the look. Once locked it is law: every change starts here, not in `app/src/styles.css`.

## Direction

A real match broadcast, cleaned up: the pitch fills the frame, and over it sits one dark plate at a time. Nothing is coloured except the two teams and the grass; the only bold graphic is the battery, a squared shell with a white charge and its number beside it. It serves a judge on a laptop who must see in seconds what the site shows; the battery says what the running would leave a typical professional, never how the player feels, so it never changes colour.

## Signature move

**The battery is one object drawn one way at every size.** A squared shell (2 px outline, 4 px radius, a filled nub), a 3 px gap, then the charge: a single flat fill whose length is the percentage. The number sits outside, right of the nub, in Saira 800 with tabular figures, its cap height equal to the shell's inner height, so bar and number read as one object. The charge is "the ink of its ground": near-white on the dark plates, the text colour on the light page. The brand mark is the same shell, empty: never filled, never a reading.

## Expressive moments

- **The lower third's battery** (Watch, Replay, Full match): the one place at full amplitude: 168 × 44 px shell, 48 px number, the charge moving continuously as the clip plays.
- Everything else holds the calm structure: play bar and tabs as quiet text, panels as rules and rows, no cards, no shadows, no fills except the current row.

## Type

- **One family: Saira** (Google Fonts, variable, `wght` 100–900, `wdth` 50–125; load `family=Saira:wdth,wght@100..125,400..800`). Fallback stack: `"Saira", "Barlow", "Segoe UI", system-ui, sans-serif`. Replaces Barlow and Barlow Condensed everywhere.
- Why: squared, superelliptic bowls (the "slightly squared sports sans"), large x-height and even texture in mixed case at 14–16 px, and a real `tnum` feature (checked in the font file; figures are proportional by default, so every number sets `font-variant-numeric: tabular-nums`).
- **Case:** mixed case everywhere. **Capitals only in the score bug** (`text-transform: uppercase`, weight 700, tracking +0.04em). Nowhere else: no uppercase headings, buttons, labels or chips. Abbreviations that are written in capitals (FB, GK, WES) are words, not styling.
- **Scale** (≈1.25 from 16 px): `--text-xs` 12 · `--text-sm` 14 · `--text-base` 16 · `--text-lg` 18 · `--text-xl` 22 · `--text-2xl` 28 · `--text-3xl` 36 · `--text-4xl` 48.
- **Weights:** 400 body · 500 labels · 600 selected tab, current row, numbers strip labels · 700 score bug, player name · 800 numbers that carry the story (score, battery %, numbers strip values).
- **Leading:** body 1.45 · tight 1.1 (names, numbers). Body text flush left, never justified; measure ≤ 70 characters in the Details lines.
- **Numbers:** every number (score, clock, %, m/s, metres, "7 / 19", shirt numbers) uses `tabular-nums`. Units keep their case ("m/s", "km/h"); m/s first, km/h in brackets.

| Role | Size | Weight | Notes |
|---|---|---|---|
| Score bug team names | `--text-base` (phone `--text-sm`) | 700 | uppercase, +0.04em; phone: three-letter codes |
| Score | `--text-xl` (phone `--text-lg`) | 800 | tabular, on `--plate-raised` |
| Match clock (bug) | `--text-base` | 600 | tabular |
| Brand name | `--text-base` | 700 | "· synthetic match" `--text-xs` 500 `--text-secondary`, same line |
| Tagline | `--text-xs` | 400 | `--text-secondary`, ≤ 2 lines |
| Lower third moment · clock | `--text-base` | 500 | `--plate-text-2` |
| Lower third player | `--text-2xl` (phone `--text-xl`) | 700 | shirt number 800 tabular; position `--text-sm` 500 `--plate-text-2` |
| Battery % | `--text-4xl` (phone `--text-3xl`) | 800 | tabular, `--charge` |
| Battery caption | `--text-xs` | 400 | `--plate-text-2`, 12 px under the gauge (clears the band brackets) |
| Play bar, tabs | `--text-sm` | 400 (selected tab 600) | |
| Numbers strip value | `--text-xl` | 800 | label `--text-xs` 500 |
| Details lines | `--text-base` | 400 | verdict label `--text-xs` |
| Footer | `--text-xs` | 400 | |

## Color tokens

Neutrals come from `palette.mjs --seed "#3b7638" --chroma muted --harmony mono` (seeded on the pitch green: grey with a trace of grass, chroma ≤ 0.018), pasted below as steps 1–12. The palette's green accent ramp and functional ramps are **not used**: the plan allows one saturated element outside the team colours (the gauge), and the gauge is drawn in charge. Broadcast tokens (plates, charge, pitch, teams) are fixed by hand and checked with the same WCAG formula (`check-contrast.mjs`, below).

**Rules that make the tokens:**

1. **Dark by default; light on `data-theme="light"`.** The theme no longer follows the device (JOURNEY sign-off 6).
2. **The pitch and the plates do not change with the theme.** The pitch is the picture; the score bug, lower third and pitch flag are dark plates in both themes. Light theme changes only the page around them (tabs, panels, play bar, footer).
3. **Team colours: the value is chosen by the ground, not the theme.** On dark grounds (pitch, plates, the dark page) the validated dark-mode pair; on the light page the validated light-mode pair. Values are today's, unchanged.
4. **Text on a team colour is dark** (`--on-team`), never white: white fails 4.5:1 on all four team values (3.20–4.42).
5. **The charge is the ink of its ground**: `--charge` on plates, `--accent-solid` (= the text colour) on the page. One colour at every level: the battery never turns red, amber or green.
6. **No hue for UI chrome.** Links, focus, selected tab and outlines use the text colours.

```css
/* Running Battery · Charge Plate tokens. Dark is the default (:root); light is opt-in. */
:root {
  color-scheme: dark;

  /* Neutrals, dark: palette.mjs --seed "#3b7638" --chroma muted --harmony mono */
  --neutral-1: #121312;
  --neutral-2: #191a19;
  --neutral-3: #212321;
  --neutral-4: #282b28;
  --neutral-5: #303330;
  --neutral-6: #393d38;
  --neutral-7: #454b45;
  --neutral-8: #5c635b;
  --neutral-9: #b1bab0;
  --neutral-10: #c4cec3;
  --neutral-11: #b3b9b3;
  --neutral-12: #e5e9e5;

  /* Semantic aliases (page) */
  --background: var(--neutral-1);
  --surface: var(--neutral-2);
  --surface-hover: var(--neutral-3);
  --surface-active: var(--neutral-4);
  --border-subtle: var(--neutral-6);
  --border: var(--neutral-7);
  --text-secondary: var(--neutral-11);
  --text: var(--neutral-12);
  --control-edge: var(--text-secondary);   /* outlined buttons (Replay, Next) */
  --focus: var(--text);                     /* 2 px focus ring, offset 2 px */
  --accent-solid: var(--text);              /* the charge on the page: gauges in Team sheet */
  --accent-on-solid: var(--background);
  --gauge-band: var(--text-secondary);      /* analyst band brackets on the page */

  /* Broadcast plates: identical in both themes */
  --plate: #191a19;
  --plate-raised: #282b28;                  /* the score cell */
  --plate-edge: #393d38;                    /* 1 px hairline where a plate meets the dark page */
  --plate-text: #e5e9e5;
  --plate-text-2: #b3b9b3;
  --charge: #f4f6f2;                        /* the battery: shell, fill, %, on plates */
  --charge-band: var(--plate-text-2);       /* analyst band brackets on plates */

  /* Teams: dark-ground pair (pitch, plates, dark page) */
  --home-on-dark: #3987e5;
  --away-on-dark: #d95926;
  --on-team: #121312;                       /* shirt numbers on markers */
  --home: var(--home-on-dark);              /* page dots, lines, chart marks */
  --away: var(--away-on-dark);

  /* Pitch: identical in both themes */
  --grass: #173a1b;
  --grass-alt: #1a3e1e;
  --pitch-line: rgba(255, 255, 255, 0.6);
  --on-pitch: #ffffff;                      /* labels on grass, with a dark halo */
  --trail: #ffffff;                         /* the star player's run */
  --warning: #fab219;                       /* hardest minutes ring, always with its Key label */

  /* Type */
  --font: "Saira", "Barlow", "Segoe UI", system-ui, sans-serif;
  --text-xs: 0.75rem;
  --text-sm: 0.875rem;
  --text-base: 1rem;
  --text-lg: 1.125rem;
  --text-xl: 1.375rem;
  --text-2xl: 1.75rem;
  --text-3xl: 2.25rem;
  --text-4xl: 3rem;
  --leading-body: 1.45;
  --leading-tight: 1.1;

  /* Space, shape, motion */
  --space-1: 4px;  --space-2: 8px;  --space-3: 12px; --space-4: 16px;
  --space-5: 24px; --space-6: 32px; --space-7: 48px;
  --radius-plate: 2px;
  --radius-shell: 4px;
  --ease-out: cubic-bezier(0.2, 0, 0, 1);
  --dur-micro: 120ms;
  --dur-standard: 200ms;
}

:root[data-theme="light"] {
  color-scheme: light;

  /* Neutrals, light: palette.mjs (same run) */
  --neutral-1: #fcfdfc;
  --neutral-2: #f8f9f8;
  --neutral-3: #eff1ef;
  --neutral-4: #e6e9e5;
  --neutral-5: #dbdfdb;
  --neutral-6: #cfd4ce;
  --neutral-7: #bfc6be;
  --neutral-8: #a6ada5;
  --neutral-9: #b1bab0;
  --neutral-10: #9fa79e;
  --neutral-11: #60655f;
  --neutral-12: #2c2f2c;

  /* Teams: light-ground pair (light page only; pitch and plates keep the dark-ground pair) */
  --home: #2a78d6;
  --away: #eb6834;
}
```

Aliases re-resolve per theme because they point at `--neutral-*`; plates, charge, pitch and the `*-on-dark` team values are not redefined in light.

**Contrast evidence** (both runs exit 0):

`palette.mjs --seed "#3b7638" --chroma muted --harmony mono` (the neutral ramps):

```
PASS [light] neutral-11 on neutral-2: 5.66:1 (4.5)   PASS [dark] neutral-11 on neutral-2: 8.78:1 (4.5)
PASS [light] neutral-12 on neutral-2: 12.89:1 (7)    PASS [dark] neutral-12 on neutral-2: 14.28:1 (7)
PASS [light] neutral-12 on neutral-3: 11.98:1 (4.5)  PASS [dark] neutral-12 on neutral-3: 12.96:1 (4.5)
(accent pairs pass too; the accent ramp is not used)
```

`check-contrast.mjs` (palette.mjs's own `luminance`/`contrast` code, run on the token block above; it parses this file, resolves every `var()` in both themes, and exits 2 on any miss). Run 2026-10-20, exit 0:

```
PASS  [dark] --text on --background: 15.18:1 (target 4.5) — body text on page
PASS  [dark] --text on --surface: 14.23:1 (target 4.5) — text on surface
PASS  [dark] --text on --surface-hover: 12.90:1 (target 4.5) — text on hover fill (buttons only)
PASS  [dark] --text-secondary on --background: 9.32:1 (target 4.5) — secondary text, tabs, play bar
PASS  [dark] --text-secondary on --surface: 8.73:1 (target 4.5) — secondary on surface
PASS  [dark] --text-secondary on --surface-hover: 7.92:1 (target 4.5) — secondary on hover fill
PASS  [dark] --accent-on-solid on --accent-solid: 15.18:1 (target 4.5) — accent-on-solid on accent-solid
PASS  [dark] --plate-text on --plate: 14.23:1 (target 4.5) — score bug names, player name
PASS  [dark] --plate-text-2 on --plate: 8.73:1 (target 4.5) — moment · clock, caption, position, flag
PASS  [dark] --plate-text on --plate-raised: 11.67:1 (target 4.5) — score on score cell
PASS  [dark] --charge on --plate: 16.05:1 (target 4.5) — battery % on plate
PASS  [dark] --on-team on --home-on-dark: 5.12:1 (target 4.5) — shirt number on home marker
PASS  [dark] --on-team on --away-on-dark: 4.80:1 (target 4.5) — shirt number on away marker
PASS  [dark] --on-pitch on --grass: 12.67:1 (target 4.5) — labels on grass
PASS  [dark] --on-pitch on --grass-alt: 11.99:1 (target 4.5) — labels on grass stripe
PASS  [dark] --charge on --plate: 16.05:1 (target 3) — battery fill vs empty part (plate) / shell vs plate
PASS  [dark] --charge-band on --plate: 8.73:1 (target 3) — analyst band brackets on plate
PASS  [dark] --accent-solid on --background: 15.18:1 (target 3) — page gauge fill/shell vs page
PASS  [dark] --accent-solid on --surface: 14.23:1 (target 3) — page gauge fill/shell vs surface
PASS  [dark] --gauge-band on --surface: 8.73:1 (target 3) — analyst band on page
PASS  [dark] --control-edge on --background: 9.32:1 (target 3) — outlined button edge (Replay, Next)
PASS  [dark] --focus on --background: 15.18:1 (target 3) — focus ring
PASS  [dark] --text on --background: 15.18:1 (target 3) — selected-tab underline
PASS  [dark] --home-on-dark on --plate: 4.80:1 (target 3) — home chip on score bug
PASS  [dark] --away-on-dark on --plate: 4.49:1 (target 3) — away chip on score bug
PASS  [dark] --home on --background: 5.12:1 (target 3) — home dot / chart line on page
PASS  [dark] --away on --background: 4.80:1 (target 3) — away dot / chart line on page
PASS  [dark] --home on --surface: 4.80:1 (target 3) — home dot on surface
PASS  [dark] --away on --surface: 4.49:1 (target 3) — away dot on surface
PASS  [dark] --home-on-dark on --grass: 3.48:1 (target 3) — home marker on grass
PASS  [dark] --home-on-dark on --grass-alt: 3.29:1 (target 3) — home marker on stripe
PASS  [dark] --away-on-dark on --grass: 3.26:1 (target 3) — away marker on grass
PASS  [dark] --away-on-dark on --grass-alt: 3.09:1 (target 3) — away marker on stripe
PASS  [dark] --trail on --grass: 12.67:1 (target 3) — run trail / star ring on grass
PASS  [dark] --warning on --grass: 6.91:1 (target 3) — hardest-minutes ring on grass
PASS  [dark] --warning on --grass-alt: 6.53:1 (target 3) — hardest-minutes ring on stripe
PASS  [dark] --charge on --grass: 11.65:1 (target 3) — pitch battery icon outline on grass
PASS  [light] --text on --background: 13.29:1 (target 4.5) — body text on page
PASS  [light] --text on --surface: 12.84:1 (target 4.5) — text on surface
PASS  [light] --text on --surface-hover: 11.93:1 (target 4.5) — text on hover fill (buttons only)
PASS  [light] --text-secondary on --background: 5.84:1 (target 4.5) — secondary text, tabs, play bar
PASS  [light] --text-secondary on --surface: 5.65:1 (target 4.5) — secondary on surface
PASS  [light] --text-secondary on --surface-hover: 5.25:1 (target 4.5) — secondary on hover fill
PASS  [light] --accent-on-solid on --accent-solid: 13.29:1 (target 4.5) — accent-on-solid on accent-solid
PASS  [light] --plate-text on --plate: 14.23:1 (target 4.5) — score bug names, player name
PASS  [light] --plate-text-2 on --plate: 8.73:1 (target 4.5) — moment · clock, caption, position, flag
PASS  [light] --plate-text on --plate-raised: 11.67:1 (target 4.5) — score on score cell
PASS  [light] --charge on --plate: 16.05:1 (target 4.5) — battery % on plate
PASS  [light] --on-team on --home-on-dark: 5.12:1 (target 4.5) — shirt number on home marker
PASS  [light] --on-team on --away-on-dark: 4.80:1 (target 4.5) — shirt number on away marker
PASS  [light] --on-pitch on --grass: 12.67:1 (target 4.5) — labels on grass
PASS  [light] --on-pitch on --grass-alt: 11.99:1 (target 4.5) — labels on grass stripe
PASS  [light] --charge on --plate: 16.05:1 (target 3) — battery fill vs empty part (plate) / shell vs plate
PASS  [light] --charge-band on --plate: 8.73:1 (target 3) — analyst band brackets on plate
PASS  [light] --accent-solid on --background: 13.29:1 (target 3) — page gauge fill/shell vs page
PASS  [light] --accent-solid on --surface: 12.84:1 (target 3) — page gauge fill/shell vs surface
PASS  [light] --gauge-band on --surface: 5.65:1 (target 3) — analyst band on page
PASS  [light] --control-edge on --background: 5.84:1 (target 3) — outlined button edge (Replay, Next)
PASS  [light] --focus on --background: 13.29:1 (target 3) — focus ring
PASS  [light] --text on --background: 13.29:1 (target 3) — selected-tab underline
PASS  [light] --home-on-dark on --plate: 4.80:1 (target 3) — home chip on score bug
PASS  [light] --away-on-dark on --plate: 4.49:1 (target 3) — away chip on score bug
PASS  [light] --home on --background: 4.33:1 (target 3) — home dot / chart line on page
PASS  [light] --away on --background: 3.14:1 (target 3) — away dot / chart line on page
PASS  [light] --home on --surface: 4.18:1 (target 3) — home dot on surface
PASS  [light] --away on --surface: 3.03:1 (target 3) — away dot on surface
PASS  [light] --home-on-dark on --grass: 3.48:1 (target 3) — home marker on grass
PASS  [light] --home-on-dark on --grass-alt: 3.29:1 (target 3) — home marker on stripe
PASS  [light] --away-on-dark on --grass: 3.26:1 (target 3) — away marker on grass
PASS  [light] --away-on-dark on --grass-alt: 3.09:1 (target 3) — away marker on stripe
PASS  [light] --trail on --grass: 12.67:1 (target 3) — run trail / star ring on grass
PASS  [light] --warning on --grass: 6.91:1 (target 3) — hardest-minutes ring on grass
PASS  [light] --warning on --grass-alt: 6.53:1 (target 3) — hardest-minutes ring on stripe
PASS  [light] --charge on --grass: 11.65:1 (target 3) — pitch battery icon outline on grass

required tokens resolved in both themes: --background --surface --text --accent-solid --text-xs --text-sm --text-base --text-lg --text-xl --text-2xl --text-3xl --text-4xl
74/74 pairs pass
```

Lowest pairs: light away dot on `--surface` 3.03 and on the page 3.14, away marker on the stripe 3.09 (all non-text, target 3); `--on-team` on the away marker 4.80 (text, target 4.5).

## The battery (mark and gauge)

| Part | On a plate (lower third, pitch icon) | On the page (Team sheet, Settings › Key) |
|---|---|---|
| Shell | 2 px outline `--charge`, radius `--radius-shell`, empty inside (the plate shows) | 1.5 px outline `--accent-solid` |
| Nub | filled `--charge`, 5 × 16 px (lower third) | filled `--accent-solid` |
| Charge (fill) | `--charge`, flat, inset 3 px from the shell on every side | `--accent-solid`, inset 2 px |
| Empty part | nothing: the plate (fill vs empty 16.05:1) | nothing: the surface |
| Percentage | outside the shell, right of the nub, `--text-4xl` 800 tabular `--charge`, min-width "100%" right-aligned | `--text-sm` 700 tabular `--text` |
| Caption | "Expected for a typical pro after the same running" (`ltBatterySub`; wording changed by the user, decision 37), `--text-xs` `--plate-text-2`, under the gauge | the sheet's sub-heading carries it |
| Analyst band | two square brackets in `--charge-band` spanning the 10th–90th percentile: a 2 px ⌐¬ above the shell and a 2 px └┘ below it, each 6 px tall, standing clear of the shell so they never cross the charge; "(71–92%)" `--text-sm` `--plate-text-2` beside the % on the same row | same shape in `--gauge-band`, 4 px tall |
| Spoken name | `role="meter"`, `aria-valuenow`, label "Battery expected for a typical pro: 83%" (+ band in Analyst) | same |

Sizes: lower third 168 × 44 px (phone 132 × 36 px); Team sheet 48 × 16 px; pitch icon 3.6 × 1.6 pitch units above the marker, shell on a `--plate` ground so it reads on grass; brand mark 24 × 12 px, 1.5 px outline, empty.

**Edge cases.**
- **Near 0%:** any value above 0 draws at least 2 px of charge; 0% draws no charge (the empty shell shows) and the number reads "0%". The number never sits inside the fill, so it never flips colour.
- **Near 100%:** the charge stops at the 3 px inset (the shell stays visible); the number box is sized for "100%", so the layout does not jump. Values are clamped to 0–100 and rounded to whole percent.
- **Never a status colour:** one charge colour at every level; no red at low values, no green at high (decision 14).
- **Band:** clamped to the inner edges; when the band is narrower than 6 px the two brackets merge into one 2 px tick with the number "(81–83%)" still shown.
- **Brand mark:** the shell only, empty, never animated: it is the name, not a reading.
- **Goalkeeper / off the pitch / team clip:** no shell at all (no empty gauge): "GK", `offPitch`, or the team slot (JOURNEY.md edge cases).

**Motion:** the charge's length eases with the clip (`width` transition 250 ms linear, as today); no pulse, no glow, no colour change. `prefers-reduced-motion`: the length jumps.

## Score bug

One plate at the column's top-left, height 36 px (phone 32 px), `--radius-plate`, 1 px `--plate-edge` on the dark page. Cells, left to right: team chip + home name · score on `--plate-raised` · away name + team chip · match clock. **Capitals only here.** Team chips are 8 × 16 px flat rectangles in `--home-on-dark` / `--away-on-dark` (4.80 / 4.49:1 on the plate), next to the outside of each name, so the chip and the markers on the pitch share one colour. Score "0–1" with an en dash, 800 tabular. Phone ≤ 520 px: three-letter codes (WES, RAV), chips stay.

## Lower third

One plate **docked directly under the pitch**, full column width, at every width (lock decision 1: nothing on the pitch is ever hidden; the pitch's height budget gives up the plate's height so the tabs stay on screen at 1440×900). Padding 12 × 20 px, `--radius-plate`, no coloured edge or block. Two columns: who (row 1: moment name · clock in `--plate-text-2`; row 2: team chip 8 × 18, shirt number 800, name 700, position `--text-sm` `--plate-text-2`) and the battery (gauge + % on one row, caption under it). Mixed case. Team clip: the battery column becomes each team's chip, full name and its metres per minute above 5.5 m/s (tabular), no shell.

## Pitch (kept; tokens only)

Mown stripes `--grass` / `--grass-alt` (7.5 m bands), lines `--pitch-line` 0.35 units; the ball stays white with a near-black edge (kept as today). Markers in the dark-ground team pair with numbers in `--on-team` (5.12 / 4.80:1), edge `rgba(0,0,0,0.5)` 0.25 units. The star player: a 0.5-unit `--on-pitch` ring; his run trail in `--trail` (thin dashed path, thick above 5.5 m/s), with an arrowhead at his current position (fix 8). Labels on grass in `--on-pitch` with a 0.5-unit dark halo. **A player the tracking lost for a moment** (a gap of at most 2.4 s, decision 38, approved by the user 2026-10-20): drawn on the straight line between where the tracking last and next saw him, the whole marker at 0.5 opacity (0.2 if also dimmed in a clip); the Key explains it. No new colour or token. Flag "Clip ended · last frame": a small plate, top-right, `--text-xs` `--plate-text-2`.

## Play bar and tab bar (quiet)

- **Play bar:** text buttons, `--text-sm` 400, `--text-secondary`, no fill, no border at rest; hover: `--text` + 1 px underline; disabled: `--border` colour (exempt from contrast); focus: 2 px `--focus` ring, offset 2 px, on `:focus-visible` only. In the Details step, Replay and Next are outlined with 1 px `--control-edge` (equal weight; never filled). Status ("Details · 7 / 19") right-aligned, `--text-secondary`, tabular. Hit area ≥ 32 px (phone 44 px).
- **Tab bar:** Clips · Team sheet · Details · Settings, `--text-sm`, `--text-secondary`; selected: `--text`, 600, 2 px underline in `--text`. A 1 px `--border-subtle` rule under the bar. No pills, no boxes.
- **Panels:** rows separated by 1 px `--border-subtle` rules; team dots 8 px in `--home`/`--away`. **No row fills:** the current row (the playing clip in Clips, the clip's player in Team sheet) is weight 600 in `--text` with a 3 px `--text` bar at its left edge and "Now playing"; hover underlines the row's name. (A neutral fill was tried: the light-theme away dot drops to 2.82:1 on `--surface-hover`, below 3:1, so the fill went, not the target.) `--surface-hover` is for button hover only. No cards, no shadows.

## Space, shape, depth

- Spacing: 4 · 8 · 12 · 16 · 24 · 32 · 48 px. Tight inside a plate (8–12), generous between bands (16–24).
- Radius: 2 px plates and buttons; 4 px battery shell; 0 elsewhere. Squared, like the type.
- Depth: none. No shadows; plates separate from the pitch by value, from the dark page by a 1 px `--plate-edge`.
- Column: one centred column the pitch's width (≈ 860 px at 1440×900; JOURNEY budget); phone 16 px gutters.

## Motion

- Timing: micro 120 ms (hover, tab underline) · standard 200 ms (lower third entering at a new clip: 8 px rise + fade, `--ease-out`) · the charge 250 ms linear.
- Never: bounce, glow, pulses on UI chrome, staggered fades. The pitch's existing "flat out" pulse stays (it is data, Full match only).
- `prefers-reduced-motion`: all transitions 0.01 ms; the charge and the lower third jump.

## Never (this project's tells at risk)

- All-caps labels outside the score bug; condensed display type; boxed labels or coloured tag blocks (today's `.lt-tag`, `.step-chip`, `.stats` boxes).
- A coloured battery, or a battery that changes colour with its level.
- A second saturated colour (no accent hue for links, focus or selection).
- Cards, nested cards, drop shadows, glow, gradients, glassmorphism.
- Navy-tinted neutrals (`#0a0c10`, `#151922`, `#1a2132`): the complaint was "dark navy cards".
- White text on a team colour.
- Inter, Roboto, Space Grotesk, Barlow Condensed.

## Styled mock (for the lock)

`.design-foundations/mocks/running-battery-styled-{watch,details,watch-light,watch-analyst}.html`, with PNGs at 1440×900 (`-1440.png`) and Watch at 390×844 (`running-battery-styled-watch-390.png`). Each file's `:root` is this token block, verbatim. Measured in the render: column 863 px; tab bar at y 704 and the panel at y 752 of 900 (Details: numbers strip and the first line above the fold); 390 px: page width 390 (no sideways scroll); 0 elements with uppercase outside the score bug; Saira loaded.

## Lock decisions (user, 2026-10-20)

1. **The lower third docks under the pitch** at every width, not over it (it hid a player and the start of his run).
2. **Phone (≤ 520 px): plain dots, no shirt numbers** (they rendered at 4–5 px); the clip's player keeps his ring and pitch battery, and his name is in the lower third. Laptop keeps the numbers.
3. **The charge stays near-white**, no hue (lemon yellow rejected: reads as a warning beside the amber ring).

Accepted with the lock: the darker grass (`#173a1b`/`#1a3e1e`, the same in both themes; today's light-theme pitch `#3b7638` retired) and dark shirt numbers (`--on-team`). Carried into the build from the Phase 2 review: 0% draws no charge (no 2 px sliver); every number tabular, including inside sentences; the analyst plate keeps a fixed width whatever the band text.
