// The overlay's data: files written by `python -m runningbattery.export` (match.json,
// positions.bin, signals.json, feed.json). All times are video_s: seconds from kick-off with
// half-time left out, as in feed.json.

export type Mode = "fan" | "analyst";

export interface Player {
  id: string;
  name: string;
  shirt: number;
  team: string;
  team_name: string;
  position: string;
  starter: boolean;
}

export interface Meta {
  match_id: string;
  pos_hz: number;
  frames: number;
  ids: string[];
  missing: number;
  periods: { period: number; video_start: number; duration_s: number }[];
  teams: { id: string; name: string; side: string; formation: string }[];
  players: Player[];
  goals: { video_s: number; team: string; scorer: string; clock: string }[];
  team_running: TeamBlock[];
  situations: string[]; // situations of play, in order (agents/tools.py SITUATIONS)
  team_situations: SituationBlock[];
  substitutions: { video_s: number; team: string; off: string; on: string; clock: string }[];
  // What each feed moment's clip shows, [start, end] (export.moment_clips, decision 38); null:
  // no clip (its player does nothing above 5.5 m/s in it); missing: the default window.
  clips?: Record<string, [number, number] | null>;
  shots?: Shot[]; // every shot, so that a clip runs on to the one its play ends in (toShot)
}

/** A shot (export.shots): when it is struck, when the ball arrives, and its team's possession's
 * first and last event, video_s. */
export interface Shot {
  video_s: number;
  arrive_s: number;
  possession_from: number;
  possession_to: number;
  team: string;
  player: string;
}

export interface TeamBlock {
  video_start: number;
  video_end: number;
  clock: string;
  home: { hsr: number | null; possession: number; in_play_s: number };
  away: { hsr: number | null; possession: number; in_play_s: number };
}

/** Where the running happened (decision 30), one 15-min block: per team and situation,
 * [metres above 5.5 m/s, ball-in-play seconds], team totals of the outfield players. */
export interface SituationBlock {
  video_start: number;
  video_end: number;
  from: string;
  to: string;
  [team: string]: Record<string, [number, number]> | number | string;
}

export interface Signals {
  start: number;
  halves?: [number, number][]; // each half's first second (video_s) and its index
  battery: number[];
  lo: number[] | null;
  hi: number[] | null;
  low_chance: number[] | null;
  hsr_1min: number[];
  speed: number[]; // decimetres per second
  red_zone: number[];
  post_peak: number[];
}

export interface Finding {
  claim: string;
  message: string;
  stage: string;
}

export interface Entry {
  t: number;
  period: number;
  clock: string;
  video_s: number;
  player: { id: string; name: string; shirt: number; team: string } | null;
  team: string;
  team_name: string;
  kind: string;
  moment_id: string;
  sentence: string;
  claim: string;
  sources: string[];
  mode: Mode;
  verdict: "pass" | "rewritten" | "fallback" | "template" | "repeat" | "blocked";
  shown: boolean;
  verifier: { stage: string; findings: Finding[] };
  original?: string;
}

export interface Feed {
  match_id: string;
  agents: Record<string, unknown>;
  moments: { moment_id: string; kind: string; clock: string; video_s: number }[];
  entries: Entry[];
}

/** A physical highlight (agents/highlights.py, decision 28): measured, with its caption. */
export interface Highlight {
  kind: "top_speed" | "longest_run" | "back_to_back" | "busiest_minute" | "most_ground"
    | "recovery_run";
  value: number;
  player: { id: string; name: string; shirt: number; team: string; position: string };
  clock: string;
  video_s: number;
  start_video_s: number;
  end_video_s: number;
  segments: [number, number][];
  caption: string;
  facts: Record<string, { value: number; unit: string; source: string } | string>;
  sources: string[];
}

export interface MatchData {
  meta: Meta;
  highlights: Highlight[];
  pos: Int16Array;
  signals: Record<string, Signals>;
  feed: Feed;
  duration: number;
}

// Labels in copy.json ("match_<id>"), checked by the Verifier with the rest of the copy.
export const MATCHES = [{ id: "story" }, { id: "natural" }];

export async function loadMatch(id: string): Promise<MatchData> {
  const base = `${import.meta.env.BASE_URL}data/${id}/`;
  const [meta, buf, signals, feed, highlights] = await Promise.all([
    fetch(base + "match.json").then((r) => r.json() as Promise<Meta>),
    fetch(base + "positions.bin").then((r) => r.arrayBuffer()),
    fetch(base + "signals.json").then((r) => r.json() as Promise<Record<string, Signals>>),
    fetch(base + "feed.json").then((r) => r.json() as Promise<Feed>),
    fetch(base + "highlights.json")
      .then((r) => (r.ok ? (r.json() as Promise<Highlight[]>) : []))
      .catch(() => []),
  ]);
  const duration = meta.periods.reduce((s, p) => s + p.duration_s, 0);
  return { meta, highlights, pos: new Int16Array(buf), signals, feed, duration };
}

/** The broadcast clock label for a replay time ("45+2:10", "67:12"). */
export function clockLabel(meta: Meta, v: number): string {
  const p2 = meta.periods.find((p) => p.period === 2);
  const second = p2 !== undefined && v >= p2.video_start;
  const t = second ? v - p2!.video_start : v;
  const c = t + (second ? 2700 : 0);
  const end = second ? 5400 : 2700;
  const mmss = (s: number) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`;
  return c >= end ? `${end / 60}+${mmss(c - end)}` : mmss(c);
}

const GAP_FILL_S = 2.4; // tracking loses a player for up to 2 s (sim/params.py DROPOUT_S)

/** Where column j must have been at replay time v while the tracking lost him for a moment:
 * straight between his positions either side of a gap of at most GAP_FILL_S (decision 38), or
 * null (no gap, or a longer one: off the pitch). Drawn faded; the estimator still sees the gap. */
export function gapFill(d: MatchData, j: number, v: number): [number, number] | null {
  const cols = d.meta.ids.length + 1;
  const hz = d.meta.pos_hz;
  const f = Math.min(Math.max(Math.round(v * hz), 0), d.meta.frames - 1);
  const at = (k: number) => (k * cols + j) * 2;
  if (d.pos[at(f)] !== d.meta.missing) return null;
  const reach = Math.ceil(GAP_FILL_S * hz);
  let a = f - 1;
  while (a >= 0 && f - a <= reach && d.pos[at(a)] === d.meta.missing) a--;
  let b = f + 1;
  while (b < d.meta.frames && b - f <= reach && d.pos[at(b)] === d.meta.missing) b++;
  if (a < 0 || b >= d.meta.frames || b - a - 1 > reach
      || d.pos[at(a)] === d.meta.missing || d.pos[at(b)] === d.meta.missing) return null;
  const w = (v * hz - a) / (b - a);
  return [
    (d.pos[at(a)] * (1 - w) + d.pos[at(b)] * w) / 10,
    (d.pos[at(a) + 1] * (1 - w) + d.pos[at(b) + 1] * w) / 10,
  ];
}

/** x, y in metres for column j at replay time v (linear between frames), or null. */
export function position(d: MatchData, j: number, v: number): [number, number] | null {
  const cols = d.meta.ids.length + 1;
  const f = Math.min(Math.max(v * d.meta.pos_hz, 0), d.meta.frames - 1);
  const a = Math.floor(f);
  const b = Math.min(a + 1, d.meta.frames - 1);
  const w = f - a;
  const ia = (a * cols + j) * 2;
  const ib = (b * cols + j) * 2;
  if (d.pos[ia] === d.meta.missing) return null;
  if (d.pos[ib] === d.meta.missing) return [d.pos[ia] / 10, d.pos[ia + 1] / 10];
  return [
    (d.pos[ia] * (1 - w) + d.pos[ib] * w) / 10,
    (d.pos[ia + 1] * (1 - w) + d.pos[ib + 1] * w) / 10,
  ];
}

/** Where each half's count starts: [video_s of its first second, its index]. The first half ends
 * mid-second (2765.7 s in the story match), so one count from `start` read the second half a
 * second late (decision 44). */
const halves = (s: Signals): [number, number][] => s.halves ?? [[s.start, 0]];

/** The last half whose `at` (0: its first second, 1: its index) is at most x, or -1. */
function lastHalf(hs: [number, number][], at: 0 | 1, x: number): number {
  let n = -1;
  hs.forEach((h, k) => { if (h[at] <= x) n = k; });
  return n;
}

/** Index into a player's per-second signals at replay time v, unbounded. */
export function signalPos(s: Signals, v: number): number {
  const hs = halves(s);
  const n = lastHalf(hs, 0, v);
  const [t0, k0] = hs[Math.max(n, 0)];
  const i = k0 + Math.floor(v - t0);
  return n >= 0 && n + 1 < hs.length ? Math.min(i, hs[n + 1][1] - 1) : i;
}

/** Index into a player's per-second signals at replay time v, or null when off the pitch. */
export function signalIndex(s: Signals | undefined, v: number): number | null {
  if (!s) return null;
  const i = signalPos(s, v);
  return i >= 0 && i < s.battery.length ? i : null;
}

/** The video_s of second k of a player's signals. */
export function signalTime(s: Signals, k: number): number {
  const hs = halves(s);
  const [t0, k0] = hs[Math.max(lastHalf(hs, 1, k), 0)];
  return t0 + k - k0;
}

export function score(meta: Meta, v: number): { home: number; away: number } {
  const done = meta.goals.filter((g) => g.video_s <= v);
  return {
    home: done.filter((g) => g.team === "home").length,
    away: done.filter((g) => g.team === "away").length,
  };
}

/** A highlight's value as the panel shows it. */
export function highlightValue(h: Highlight): string {
  const f = (k: string) => {
    const x = h.facts[k];
    return typeof x === "string" ? x : x?.value;
  };
  if (h.kind === "top_speed") return `${Number(f("top_speed")).toFixed(1)} m/s`;
  if (h.kind === "longest_run") return `${f("metres")} m`;
  if (h.kind === "back_to_back") return `${f("runs")} runs in ${f("seconds")} s`;
  if (h.kind === "most_ground") return `${Number(f("km")).toFixed(1)} km`;
  if (h.kind === "recovery_run") return `${f("metres")} m back`;
  return `${f("metres_in_one_minute")} m`;
}

/** One clip of the Highlights view (decision 29): a highlight or a feed moment, shown first
 * as it happened, then its details on the last frame; a Replay button plays it again slowed down
 * (decision 34). */
export interface Item {
  id: string;
  source: "highlight" | "moment";
  kind: string; // highlight kind or moment kind
  player: string | null; // null for a team moment
  team: string;
  clock: string;
  at: number; // the key second (video_s)
  start: number; // the clip, video_s
  end: number;
  segments: [number, number][]; // his high-speed runs in the clip
  caption: string;
  h?: Highlight;
  momentId?: string;
  momentKind?: string; // the feed moment's kind, also when it shares a highlight's clip
  lapse: boolean; // the whole match at once (most ground covered)
}

const MOMENT_BEFORE = 8; // a moment's clip: from 8 s before to 4 s after (our choice)
const MOMENT_AFTER = 4;
const HI_SPEED = 55; // decimetres per second: 5.5 m/s, where high-speed running starts

/** The seconds above 5.5 m/s in [a, b] for one player, as runs. */
export function fastSegments(s: Signals | undefined, a: number, b: number): [number, number][] {
  const out: [number, number][] = [];
  if (!s) return out;
  for (let v = Math.ceil(a); v <= b; v++) {
    const i = signalIndex(s, v); // a substitute's signals start mid-second
    const fast = i !== null && s.speed[i] > HI_SPEED && s.speed[i] <= 110;
    const last = out[out.length - 1];
    if (fast && last && last[1] === v) last[1] = v + 1;
    else if (fast) out.push([v, v + 1]);
  }
  return out;
}

/** A highlight clip fast-forwards the stretches between a player's high-speed runs (decision 39:
 * a back-to-back or busiest-minute clip ran a minute at 1×, mostly between his runs): from
 * 1.5 s after one run to 2 s before the next, if that is 3 s or more, and never the clip's
 * first 1.5 s. */
export const FAST_FORWARD = 4;
export function quietGaps(runs: [number, number][], from: number, to: number): [number, number][] {
  const out: [number, number][] = [];
  let a = from + 1.5;
  for (const [s0, s1] of [...runs, [to + 2, to + 2]]) {
    const b = Math.min(s0 - 2, to);
    if (b - a >= 3) out.push([a, b]);
    a = Math.max(a, s1 + 1.5);
  }
  return out;
}

/** A clip whose play is still on when it ends and ends in a shot runs on to the ball's arrival
 * (decision 46: clips stopped a few seconds before the shot their play ended in). The play on
 * screen at the clip's last second (2 s after its window, `clipTo`) is the possession then on;
 * its first shot not landed before the clip counts if it comes within SHOT_REACH_S of that
 * second, in the same half (a rebound later in the same possession does not). */
export const SHOT_REACH_S = 20;
export function toShot(d: MatchData, it: Item): Item {
  if (it.lapse) return it;
  const shown = it.end + 2;
  const half = d.meta.periods.filter((p) => p.video_start <= it.start).at(-1);
  const halfEnd = half ? half.video_start + half.duration_s : Infinity;
  // The first shot of the play on screen that has not landed before the clip starts; none if
  // the clip already shows it.
  const s = (d.meta.shots ?? []).find((x) => x.possession_from <= shown && x.possession_to >= shown
                                             && x.arrive_s > it.start && x.video_s < halfEnd);
  return s && s.arrive_s > shown && s.video_s - shown <= SHOT_REACH_S
    ? { ...it, end: s.arrive_s } : it;
}

export function itemOfHighlight(h: Highlight): Item {
  const lapse = h.kind === "most_ground";
  return {
    id: `hl:${h.kind}:${h.player.id}:${h.video_s}`, source: "highlight", kind: h.kind,
    player: h.player.id, team: h.player.team, clock: h.clock,
    at: h.kind === "recovery_run" ? h.start_video_s : h.video_s,
    start: lapse ? 0 : h.start_video_s, end: h.end_video_s, segments: h.segments,
    caption: h.caption, h, lapse,
  };
}

/** Seconds two clips share. */
/** Seconds a clip plays around its window: 3 before, 2 after (App.tsx `clipFrom`, `clipTo`). */
const PLAYED_PAD = 5;
const SHARE_MAX = 2; // s two clips of different players may share (clip_audit's "shares")
// A highlight of the moment's player that runs on past the moment's clip gives way to it, so that
// the clip ends on the second its line is about (decision 42: a back-to-back clip 37 s past a
// hardest-minutes moment ended on 48% under the line's 57%).
const RUNS_ON_S = 1;

function overlap(a: Item, b: Item): number {
  return Math.min(a.end, b.end) - Math.max(a.start, b.start);
}

/** The Highlights view's clips in match order: the match's best highlights (as the reel) and
 * the feed's moments, each with its first verified line in this mode. One clip per action
 * (decision 38): a moment that shares more than half of the shorter clip with a highlight of the
 * same player becomes that clip's line; one that shares more than half of the shorter clip with
 * another player's highlight (the same action seen twice; decision 40, the longer clip before)
 * takes its place; one that shares more than half of the shorter clip with a moment already in
 * the list (the same action, from either side) gets no clip. A moment whose played clip touches
 * the same player's highlight (3 s before and 2 s after each, `clipFrom`/`clipTo` in App.tsx)
 * also becomes that clip's line, so his two clips do not replay the same seconds (decision 40).
 * One whose played clip shares more than SHARE_MAX seconds with another player's highlight takes
 * its place too, and one that shares that much with another player's moment already in the list
 * gets no clip (decision 41: a clip of his hardest minutes replayed the last 8 s of a
 * team-mate's back-to-back runs). */
export function queue(d: MatchData, mode: Mode, best: Highlight[]): Item[] {
  const items = best.map((h) => toShot(d, itemOfHighlight(h)));
  const moments: Item[] = [];
  for (const m of d.feed.moments) {
    const lines = d.feed.entries.filter((e) => e.moment_id === m.moment_id && e.mode === mode
                                               && e.shown);
    if (!lines.length) continue;
    const window = d.meta.clips?.[m.moment_id];
    if (window === null) continue; // nothing to see: the line stays in the full match
    const e = lines[0];
    const pid = e.player?.id ?? null;
    if (!pid) continue; // a team moment: a statistic of 15 minutes, in the Stats tab (decision 46)
    const [start, end] = window
      ?? [Math.max(m.video_s - MOMENT_BEFORE, 0), m.video_s + MOMENT_AFTER];
    moments.push(toShot(d, {
      id: m.moment_id, source: "moment", kind: m.kind, player: pid, team: e.team,
      clock: window ? clockLabel(d.meta, start) : m.clock, at: window ? start : m.video_s,
      start, end, segments: fastSegments(d.signals[pid], start, end),
      caption: e.sentence, momentId: m.moment_id, momentKind: m.kind, lapse: false,
    }));
  }
  const shared = (a: Item, b: Item) =>
    !a.lapse && (overlap(a, b) > 0.5 * Math.min(a.end - a.start, b.end - b.start)
                 || (a.player !== b.player && overlap(a, b) > SHARE_MAX - PLAYED_PAD));
  const out: Item[] = [];
  for (const m of moments) {
    // The same run again, or the same action seen from another player (decision 39: a defender
    // caught on the break and the attacker's flat-out run on that counter); its lines stay in
    // the full match.
    const len = (x: Item) => x.end - x.start;
    if (out.some((o) => overlap(o, m) > 0.5 * Math.min(len(o), len(m))
                        || (o.player !== m.player && overlap(o, m) > SHARE_MAX - PLAYED_PAD))) {
      continue;
    }
    let k = items.findIndex((h) => shared(h, m));
    if (k < 0 && m.player) {
      k = items.findIndex((h) => !h.lapse && !h.momentId && h.player === m.player
                                 && overlap(h, m) > -PLAYED_PAD);
    }
    if (k < 0) {
      out.push(m);
    } else if (items[k].player === m.player && !items[k].momentId
               && items[k].end <= m.end + RUNS_ON_S) {
      const h = items[k];
      items[k] = { ...h, momentId: m.momentId, momentKind: m.kind,
                   start: Math.min(h.start, m.start), end: Math.max(h.end, m.end) };
    } else {
      items.splice(k, 1);
      out.push(m);
    }
  }
  return [...items, ...out].sort((a, b) => a.at - b.at);
}

/** The top n so far of one kind, one per player (the best of each), best first. */
export function topSoFar(all: Highlight[], kind: Highlight["kind"], now: number, n = 3): Highlight[] {
  const best = new Map<string, Highlight>();
  for (const h of all) {
    if (h.kind !== kind || h.video_s > now) continue;
    const b = best.get(h.player.id);
    if (!b || h.value > b.value) best.set(h.player.id, h);
  }
  return [...best.values()].sort((a, b) => b.value - a.value).slice(0, n);
}
