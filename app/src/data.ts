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
  favourite?: string | null; // the feed was made for this player (--favourite)
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

/** Index into a player's per-second signals at replay time v, or null when off the pitch. */
export function signalIndex(s: Signals | undefined, v: number): number | null {
  if (!s) return null;
  const i = Math.floor(v - s.start);
  return i >= 0 && i < s.battery.length ? i : null;
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
    const i = Math.floor(v - s.start); // a substitute's signals start mid-second
    const fast = i >= 0 && i < s.speed.length && s.speed[i] > HI_SPEED && s.speed[i] <= 110;
    const last = out[out.length - 1];
    if (fast && last && last[1] === v) last[1] = v + 1;
    else if (fast) out.push([v, v + 1]);
  }
  return out;
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
function overlap(a: Item, b: Item): number {
  return Math.min(a.end, b.end) - Math.max(a.start, b.start);
}

/** The Highlights view's clips in match order: the match's best highlights (as the reel) and
 * the feed's moments, each with its first verified line in this mode. One clip per action
 * (decision 38): a moment that shares more than half of the shorter clip with a highlight of the
 * same player becomes that clip's line; one that shares more than half of the longer clip with
 * another player's highlight (the same run seen twice) takes its place. */
export function queue(d: MatchData, mode: Mode, best: Highlight[]): Item[] {
  const items = best.map(itemOfHighlight);
  const moments: Item[] = [];
  for (const m of d.feed.moments) {
    const lines = d.feed.entries.filter((e) => e.moment_id === m.moment_id && e.mode === mode
                                               && e.shown);
    if (!lines.length) continue;
    const window = d.meta.clips?.[m.moment_id];
    if (window === null) continue; // nothing to see: the line stays in the full match
    const e = lines[0];
    const pid = e.player?.id ?? null;
    const [start, end] = window
      ?? [Math.max(m.video_s - MOMENT_BEFORE, 0), m.video_s + MOMENT_AFTER];
    moments.push({
      id: m.moment_id, source: "moment", kind: m.kind, player: pid, team: e.team,
      clock: window ? clockLabel(d.meta, start) : m.clock, at: window ? start : m.video_s,
      start, end, segments: pid ? fastSegments(d.signals[pid], start, end) : [],
      caption: e.sentence, momentId: m.moment_id, momentKind: m.kind, lapse: false,
    });
  }
  const shared = (a: Item, b: Item) => {
    const len = a.player === b.player ? Math.min : Math.max;
    return !a.lapse && overlap(a, b) > 0.5 * len(a.end - a.start, b.end - b.start);
  };
  const out: Item[] = [];
  for (const m of moments) {
    if (out.some((o) => o.player === m.player && shared(o, m))) continue; // the same run again
    const k = items.findIndex((h) => shared(h, m));
    if (k < 0) {
      out.push(m);
    } else if (items[k].player === m.player && !items[k].momentId) {
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
