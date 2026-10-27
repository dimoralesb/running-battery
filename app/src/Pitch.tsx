import { useMemo } from "react";
import copy from "./copy.json";
import {
  type Item, type MatchData, type Mode, type Signals, gapFill, highlightValue, position,
  signalIndex, signalTime,
} from "./data";

// Pitch 105 × 68 m, centre origin (schema). y is drawn upwards.
const L = 105;
const W = 68;
// Flat out (as agents/tools.py): a second at ≥ 90% of his top speed so far, from
// the 10th minute, top so far ≥ 7.0 m/s; faster than 11 m/s is a tracking error.
const FLAT_SHARE = 0.9;
const FLAT_MIN = 70; // decimetres per second
const FLAT_FROM = 600;
const PLAUSIBLE = 110;
const PULSE_S = 3; // match seconds the pulse lasts
const TRAIL_STEP = 0.2; // s between trail points (the positions are at 5 Hz)
const LAPSE_STEP = 2; // s between trail points for a whole match (most ground covered)
const STRIPES = 12; // mown stripes across the pitch, as on a broadcast
const FADE_STEPS = 6; // the trail fades towards its start in this many steps, so it shows direction

// Three views: the full match, and a clip's Watch and Replay-with-details steps,
// which show only the clip's player path.
export type View = "full" | "watch" | "replay";

interface Props {
  data: MatchData;
  now: number;
  mode: Mode;
  view: View;
  selected: string | null;
  allBatteries: boolean;
  item: Item | null; // the clip (watch and replay)
  focus: string | null; // full match: the player of the feed moment on screen
  flatLabel: string;
  onSelect: (id: string) => void;
}

function Markings() {
  const box = (sign: number, depth: number, half: number) => (
    <rect x={sign > 0 ? L / 2 - depth : -L / 2} y={-half} width={depth} height={2 * half} />
  );
  return (
    <g className="lines">
      <rect x={-L / 2} y={-W / 2} width={L} height={W} />
      <line x1={0} y1={-W / 2} x2={0} y2={W / 2} />
      <circle cx={0} cy={0} r={9.15} />
      {box(-1, 16.5, 20.16)}
      {box(1, 16.5, 20.16)}
      {box(-1, 5.5, 9.16)}
      {box(1, 5.5, 9.16)}
    </g>
  );
}

/** The typical-pro battery as a continuous fill. */
function BatteryIcon({ pct, x, y }: { pct: number; x: number; y: number }) {
  const w = 5.0 * Math.min(Math.max(pct, 0), 100) / 100;
  return (
    <g transform={`translate(${x - 2.6} ${y})`} className="battery">
      <rect x={-0.15} y={-0.15} width={5.3} height={1.3} rx={0.3} className="shell" />
      <rect x={0.05} y={0.05} width={5.0} height={0.9} rx={0.15} className="cell" />
      {w > 0 && <rect x={0.05} y={0.05} width={w} height={0.9} rx={0.15} className="cell full" />}
      <rect x={5.2} y={0.3} width={0.25} height={0.5} className="nub" />
    </g>
  );
}

/** The video_s of each flat-out run's fastest second, per player. */
function flatOutPeaks(s: Signals): number[] {
  const out: number[] = [];
  let top = 0;
  let run: [number, number] | null = null; // [second, speed] of the fastest second so far
  s.speed.forEach((raw, k) => {
    const v = raw <= PLAUSIBLE ? raw : 0;
    const hot = signalTime(s, k) >= FLAT_FROM && top >= FLAT_MIN && v >= FLAT_SHARE * top;
    if (hot) run = run && run[1] >= v ? run : [k, v];
    else if (run) {
      out.push(signalTime(s, run[0]));
      run = null;
    }
    top = Math.max(top, v);
  });
  if (run) out.push(signalTime(s, (run as [number, number])[0]));
  return out;
}

export function Legend({ mode, text }: { mode: Mode; text: Record<string, string> }) {
  return (
    <details className="legend-box">
      <summary>{text.key}</summary>
      <div className="legend">
        <span><svg viewBox="-1.2 -1.2 2.4 2.4" className="key"><circle r={0.9} className="focus-key" /></svg>
          {text.legendFocus}</span>
        <span><svg viewBox="-1.2 -1.2 2.4 2.4" className="key"><circle r={0.9} className="redzone-key" /></svg>
          {text.legendRedZone}</span>
        <span><svg viewBox="-1.2 -1.2 2.4 2.4" className="key"><circle r={0.9} className="flat-key" /></svg>
          {text.legendFlatOut}</span>
        <span><svg viewBox="-1.2 -1.2 2.4 2.4" className="key"><circle r={0.8} className="est-key" /></svg>
          {text.legendGap}</span>
        {mode === "fan" && (
          <span><svg viewBox="-3 -0.4 6 1.8" className="key wide"><BatteryIcon pct={60} x={0} y={0} /></svg>
            {text.legendBattery}</span>
        )}
      </div>
    </details>
  );
}

/** The clip's player path from its start to now: thin, with his high-speed runs (the clip's
 * segments) drawn thick, fading towards its start and with an arrowhead where he is, so it shows
 * which way he ran; a highlight's value at the end once it is over. */
function Trail({ data, item, now, j }: { data: MatchData; item: Item; now: number; j: number }) {
  if (now < item.start - 3) return null;
  const until = Math.min(now, item.end);
  const step = item.lapse ? LAPSE_STEP : TRAIL_STEP;
  const pts: [number, number, number][] = [];
  for (let v = item.start; v <= until + 1e-6; v += step) {
    const p = position(data, j, v);
    if (p) pts.push([p[0], -p[1], v]);
  }
  if (pts.length < 2) return null;
  const d = (ps: [number, number, number][]) =>
    ps.map(([x, y], k) => `${k ? "L" : "M"}${x.toFixed(2)},${y.toFixed(2)}`).join("");
  const runs = item.segments.map(([a, b]) => pts.filter(([, , v]) => v >= a - 1e-6 && v <= b + 1e-6))
    .filter((ps) => ps.length > 1);
  const [ex, ey] = pts[pts.length - 1];
  // The direction at the end, from a point about a second back (for the arrowhead).
  const [bx, by] = pts[Math.max(pts.length - 1 - Math.round(1 / step), 0)];
  const len = Math.hypot(ex - bx, ey - by);
  const [ux, uy] = len > 0.3 ? [(ex - bx) / len, (ey - by) / len] : [0, 0];
  const t0 = pts[0][2];
  const span = Math.max(pts[pts.length - 1][2] - t0, 1e-6);
  const fade = (v: number) => 0.3 + 0.7 * Math.min(Math.floor(((v - t0) / span) * FADE_STEPS) + 1, FADE_STEPS) / FADE_STEPS;
  // Split into steps of equal time, each drawn more opaque than the one before.
  const chunks = (ps: [number, number, number][]) => {
    const out: { ps: [number, number, number][]; o: number }[] = [];
    for (const p of ps) {
      const o = fade(p[2]);
      const last = out[out.length - 1];
      if (last && last.o === o) last.ps.push(p);
      else out.push({ ps: last ? [last.ps[last.ps.length - 1], p] : [p], o });
    }
    return out.filter((c) => c.ps.length > 1);
  };
  return (
    <g className={`trail${item.lapse ? " lapse" : ""}`}>
      {chunks(pts).map((c, k) => <path key={k} d={d(c.ps)} className="trail-path" style={{ opacity: c.o }} />)}
      {runs.flatMap((ps, k) => chunks(ps).map((c, m) => (
        <path key={`${k}-${m}`} d={d(c.ps)} className="trail-run" style={{ opacity: c.o }} />
      )))}
      {(ux !== 0 || uy !== 0) && (
        <path className="trail-arrow" d={`M${(ex + ux * 3.9).toFixed(2)},${(ey + uy * 3.9).toFixed(2)}`
          + `L${(ex + ux * 2.6 - uy * 1.0).toFixed(2)},${(ey + uy * 2.6 + ux * 1.0).toFixed(2)}`
          + `L${(ex + ux * 2.6 + uy * 1.0).toFixed(2)},${(ey + uy * 2.6 - ux * 1.0).toFixed(2)}Z`} />
      )}
      {item.h && now >= item.end && <OnPitchText x={ex} y={ey + 5} gap={3.2} size={2.4}
                                                  className="trail-label" text={highlightValue(item.h)} />}
    </g>
  );
}

/** Text beside a point, to its right, or to its left near the right touchline, so it is never cut
 * off by the pitch's edge ("7 runs in 55 s" ran off it). */
function OnPitchText({ x, y, gap, size, className, text }: {
  x: number; y: number; gap: number; size: number; className: string; text: string;
}) {
  const width = text.length * size * 0.6; // a generous estimate for the bold UI font
  const left = x + gap + width > L / 2 + 1.5;
  return (
    <text x={left ? x - gap : x + gap} y={Math.min(y, W / 2 + 1.5)} textAnchor={left ? "end" : "start"}
          className={className}>{text}</text>
  );
}

export function Pitch({ data, now, mode, view, selected, allBatteries, item, focus, flatLabel,
                        onSelect }: Props) {
  const { meta } = data;
  const ball = position(data, meta.ids.length, now);
  const peaks = useMemo(
    () => Object.fromEntries(Object.entries(data.signals).map(([id, s]) => [id, flatOutPeaks(s)])),
    [data],
  );
  const col = useMemo(() => Object.fromEntries(meta.players.map((p, j) => [p.id, j])), [meta]);
  const clip = view !== "full" && item ? item : null;

  // Where everyone is. In the full match only the players in focus (selected, the feed
  // moment's player) get rings and pulses, so there is one obvious place to look.
  const here = meta.players.map((p, j) => {
    const seen = position(data, j, now);
    const xy = seen ?? gapFill(data, j, now); // lost by the tracking for a moment: faded
    const s = data.signals[p.id];
    return { p, xy, est: !seen && !!xy, s, i: xy ? signalIndex(s, now) : null };
  });
  const inFocus = (id: string) => id === selected || id === focus;
  const showBattery = (id: string) => allBatteries || id === selected;

  return (
    <svg className={`pitch view-${view}`} viewBox={`${-L / 2 - 2} ${-W / 2 - 2} ${L + 4} ${W + 4}`}
         role="img" aria-label={copy.pitchLabel}>
      <rect x={-L / 2 - 2} y={-W / 2 - 2} width={L + 4} height={W + 4} className="grass" />
      {Array.from({ length: STRIPES }, (_, k) => (
        <rect key={k} x={-L / 2 + (k * L) / STRIPES} y={-W / 2 - 2} width={L / STRIPES} height={W + 4}
              className={k % 2 ? "stripe" : "stripe alt"} />
      ))}
      <Markings />
      {clip && clip.player && clip.player in col && (
        <Trail data={data} item={clip} now={now} j={col[clip.player]} />
      )}
      {here.map(({ p, xy, est, s, i }) => {
        if (!xy) return null;
        const [x, y] = [xy[0], -xy[1]];
        const isSel = p.id === selected;
        const star = clip ? p.id === clip.player : inFocus(p.id);
        // A team clip has no star player, so nothing is dimmed; a player clicked during a clip
        // is not dimmed and shows his battery.
        const picked = !!clip && isSel && !star;
        const dim = clip && clip.player ? !star && !picked : false;
        const red = !clip && star && i !== null && s.red_zone[i] === 1;
        const since = clip || !star ? undefined
          : (peaks[p.id] ?? []).map((v) => now - v).find((d) => d >= 0 && d < PULSE_S);
        return (
          <g key={p.id}
             className={`player ${p.team}${isSel ? " sel" : ""}${dim ? " dim" : ""}${est ? " est" : ""}`}
             onClick={() => onSelect(p.id)} role="button" aria-label={`${p.shirt} ${p.name}`}>
            <circle cx={x} cy={y} r={3} className="hit" />
            {since !== undefined && (
              <>
                <circle cx={x} cy={y} r={2 + 1.6 * since} className="pulse"
                        style={{ opacity: 1 - since / PULSE_S }} />
                <text x={x + 2.6} y={y + 3.4} className="flat-label">{flatLabel}</text>
              </>
            )}
            {red && <circle cx={x} cy={y} r={2.3} className="redzone" />}
            {!clip && p.id === focus && <circle cx={x} cy={y} r={2.9} className="focus" />}
            {clip && star && <circle cx={x} cy={y} r={2.3} className="focus" />}
            <circle cx={x} cy={y} r={1.45} className="dot" />
            <text x={x} y={y + 0.55} className="shirt">{p.shirt}</text>
            {i !== null && p.position !== "GK"
             && (clip ? star || picked : mode === "fan" && showBattery(p.id)) && (
              <BatteryIcon pct={s.battery[i]} x={x} y={y - 3.6} />
            )}
            {picked && i !== null && p.position !== "GK" && (
              <OnPitchText x={x} y={y - 2.3} gap={3.4} size={2.2} className="trail-label"
                           text={`${s.battery[i]}%`} />
            )}
          </g>
        );
      })}
      {ball && <circle cx={ball[0]} cy={-ball[1]} r={0.7} className="ball" />}
    </svg>
  );
}
