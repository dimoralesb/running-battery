# Running Battery: overlay redesign brief

**Summary:** Rework the match overlay (`app/`) into a cleaned-up TV broadcast graphic where the
battery (what the running would leave a typical pro) is the one bold element and everything else
waits in tabs under the pitch.

- Date: 2026-10-20
- Status: **draft**
- Project: hackathon entry (Microsoft x Premier League "Inside the Game"), submit Tue 27 Oct 2026.
  Formerly "Second Wind"; renamed **Running Battery** this session.

## What it is

An overlay plus a team of verified AI agents that shows, from tracking positions alone, each
player's hard (high-speed) running and what that running would leave a typical professional (the
"battery"). It opens on the match's highlights: a clip plays once at 1x, then its details (numbers,
feed lines with sources and verdicts), with a slow-motion replay on request.

## Who and where

- **Main viewer: hackathon judges on a laptop** (also the demo video, recorded at laptop width).
  Phone (360/390 px) must still work with no sideways scroll, but it is not the design target.
- Secondary: a fan (default "Fan" mode) and an analyst ("Analyst" mode: bands, sources).

## What's wrong now (user's words, 2026-10-20)

- **Too much at once.** Header with four controls, score bug, two "fastest so far" lines, a list
  of 19 clips, the lower third and the team sheet all compete; nowhere obvious to look.
- **Looks like any dashboard.** Dark navy cards, condensed capitals, coloured blocks: generic.

## Direction

- **Feel: TV broadcast, cleaned up.** Like a real broadcast overlay: one graphic at a time over a
  full-width pitch.
- **While a clip plays, on screen only:** the score bug and **one lower third** (moment, player,
  his battery with percentage). No feed lines during playback; they come with the details after
  the clip.
- **Everything else in tabs under the pitch:** Clips (the 19 highlights), Team sheet (every
  player's battery), Feed (the agents' lines), and the pickers (Highlights/Full match, match,
  Fan/Analyst, favourite player). One tab open at a time.
- **Signature: the battery is the brand.** The battery shape is the logo and the only bold
  graphic; the rest stays quiet and neutral.
- **Real broadcast type:** fewer capitals and boxed labels, a proper type pairing, more empty
  space, like a premium sports channel's graphics.
- Keep: the green pitch, the two team colours (the validated pair), light and dark themes.

## Constraints (fixed, from the project)

- Decision 14: the battery always says it is what the running would leave **a typical
  professional**, never the player's own state. The name "Running Battery" invites "his battery",
  so the subtitle "what the running would leave a typical pro" goes wherever the name does.
- Every sentence on screen, including fixed UI text in `app/src/copy.json`, passes the Verifier.
  Words: "his hardest minutes", never "spell"; no "pressing"; teams named in full; m/s first,
  km/h in brackets; no effort or intent read from speed; no team-level tiredness.
- No third-party trademarks (no broadcaster or league marks in the look or the video).
- Stack: React 18.3.1 + Vite 5.4.11 + TypeScript, static site on Azure Static Web Apps (Free).
- URL state must keep working (`view`, `match`, `t`, `mode`, `player`, `favourite`, `theme`,
  `batteries`, `hl`, `moment`, `item`, `step`, `auto`).
- Goalkeepers get no battery. Analyst mode keeps the 10-90% band.
- Time: about six working days before submission (Tue 27 Oct 2026); the demo video follows.

## Taste signals

- Broadcast over editorial or "quiet app" (both offered and passed over).
- Wants the battery to carry the identity, not colour blocks or panels.
- Dislikes all-caps condensed labels in boxes everywhere (current Barlow Condensed look).
- Did not ask for a different pitch: keep the mown green with white lines.
- Wants names concrete and literal ("tracker", "battery") over idioms.

## Open questions

- Visual identity / design DNA: the type pairing (replacing Barlow Condensed everywhere?) and
  the battery mark as a logo.
- Default theme for judges: dark (TV feel) or light?
- Where "fastest so far" and the score bug's details go once the header is cleared.
- How the details step (after a clip) looks within the tabs model: does it open the Feed tab, or
  sit in the lower third?
- Full-match view: same lower third and tabs, or its own layout?
