import { useMemo } from "react";
import {
  type Item, type MatchData, type Mode, type Signals, fanLevel, highlightValue, position,
  signalIndex,
} from "./data";

// Pitch 105 × 68 m, centre origin (schema). y is drawn upwards.
const L = 105;
const W = 68;
// Flat out (decision 24, as agents/tools.py): a second at ≥ 90% of his top speed so far, from
// the 10th minute, top so far ≥ 7.0 m/s; faster than 11 m/s is a tracking error.
const FLAT_SHARE = 0.9;
const FLAT_MIN = 70; // decimetres per second
const FLAT_FROM = 600;
const PLAUSIBLE = 110;
const PULSE_S = 3; // match seconds the pulse lasts
// Reachable area in 1 s [Narizuka2023, p.5–6]: the Fujimura–Sugihara model with the paper's
// fit at Δt = 1 s (α 1.23 1/s, V_max 14.53 m/s): centre x + A·v, radius V_max·(Δt − A),
// A = (1 − e^(−αΔt))/α ≈ 0.576, radius ≈ 6.2 m (the paper's 6.16 m). v is the 1-s difference
// of positions, as in the paper (p.2).
const ALPHA = 1.23;
const VMAX = 14.53;
const REACH_A = (1 - Math.exp(-ALPHA)) / ALPHA;
const REACH_R = VMAX * (1 - REACH_A);
const REACH_WINDOW = 6; // shown from 6 s before to 6 s after the clip's key second
const REACH_OPPONENTS = 2;
const TRAIL_STEP = 0.2; // s between trail points (the positions are at 5 Hz)
const LAPSE_STEP = 2; // s between trail points for a whole match (most ground covered)

// Three views (decision 29): the full match, and a clip's Watch and Replay-with-details steps,
// which show only the clip's player path (and the reachable areas at a turnover).
export type View = "full" | "watch" | "replay";

interface Props {
  data: MatchData;
  now: number;
  mode: Mode;
  view: View;
  selected: string | null;
  favourite: string | null;
  allBatteries: boolean;
  item: Item | null; // the clip (watch and replay)
  focus: string | null; // full match: the player of the feed moment on screen
  reachLabel: string;
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

/** Five cells; filled cells = the fan level of the typical-pro battery. */
function BatteryIcon({ pct, x, y }: { pct: number; x: number; y: number }) {
  const level = fanLevel(pct);
  return (
    <g transform={`translate(${x - 2.6} ${y})`} className="battery">
      <rect x={-0.15} y={-0.15} width={5.3} height={1.3} rx={0.3} className="shell" />
      {[0, 1, 2, 3, 4].map((k) => (
        <rect key={k} x={k * 1.04 + 0.05} y={0.05} width={0.9} height={0.9} rx={0.15}
              className={k < level ? "cell full" : "cell"} />
      ))}
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
    const hot = s.start + k >= FLAT_FROM && top >= FLAT_MIN && v >= FLAT_SHARE * top;
    if (hot) run = run && run[1] >= v ? run : [k, v];
    else if (run) {
      out.push(s.start + run[0]);
      run = null;
    }
    top = Math.max(top, v);
  });
  if (run) out.push(s.start + (run as [number, number])[0]);
  return out;
}

export function Legend({ mode, text, allBatteries, onAllBatteries }: {
  mode: Mode;
  text: Record<string, string>;
  allBatteries: boolean;
  onAllBatteries: (b: boolean) => void;
}) {
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
        {mode === "fan" && (
          <>
            <span><svg viewBox="-3 -0.4 6 1.8" className="key wide"><BatteryIcon pct={60} x={0} y={0} /></svg>
              {text.legendBattery}</span>
            <label className="check">
              <input type="checkbox" checked={allBatteries}
                     onChange={(e) => onAllBatteries(e.target.checked)} />
              {allBatteries ? text.batteriesAll : text.batteriesSome}
            </label>
          </>
        )}
        <span><svg viewBox="-1.2 -1.2 2.4 2.4" className="key"><circle r={0.8} className="fav-key" /></svg>
          {text.legendFavourite}</span>
      </div>
    </details>
  );
}

/** The clip's player path from its start to now: thin, with his high-speed runs (the clip's
 * segments) drawn thick, and a highlight's value at the end once it is over. */
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
  return (
    <g className={`trail ${item.team}${item.lapse ? " lapse" : ""}`}>
      <path d={d(pts)} className="trail-path" />
      {runs.map((ps, k) => <path key={k} d={d(ps)} className="trail-run" />)}
      {item.h && now >= item.end && (
        <text x={ex + 3.2} y={ey - 3.2} className="trail-label">{highlightValue(item.h)}</text>
      )}
    </g>
  );
}

export function Pitch({ data, now, mode, view, selected, favourite, allBatteries, item, focus,
                        reachLabel, flatLabel, onSelect }: Props) {
  const { meta } = data;
  const ball = position(data, meta.ids.length, now);
  const peaks = useMemo(
    () => Object.fromEntries(Object.entries(data.signals).map(([id, s]) => [id, flatOutPeaks(s)])),
    [data],
  );
  const col = useMemo(() => Object.fromEntries(meta.players.map((p, j) => [p.id, j])), [meta]);
  const clip = view !== "full" && item ? item : null;

  // Where everyone is. In the full match only the players in focus (selected, favourite, the
  // feed moment's player) get rings and pulses, so there is one obvious place to look.
  const here = meta.players.map((p, j) => {
    const xy = position(data, j, now);
    const s = data.signals[p.id];
    return { p, xy, s, i: xy ? signalIndex(s, now) : null };
  });
  const inFocus = (id: string) => id === selected || id === favourite || id === focus;
  const showBattery = (id: string) => allBatteries || id === selected || id === favourite;

  // Reachable areas (model) at a clip's turnover: the player and his nearest opponents.
  const reach: { id: string; team: string; cx: number; cy: number; main: boolean }[] = [];
  if (clip && clip.reach && clip.player && clip.player in col
      && Math.abs(now - clip.at) <= REACH_WINDOW) {
    const me = here[col[clip.player]];
    if (me.xy) {
      const others = here
        .filter((h) => h.xy && h.p.team !== me.p.team)
        .map((h) => ({ h, d: Math.hypot(h.xy![0] - me.xy![0], h.xy![1] - me.xy![1]) }))
        .sort((a, b) => a.d - b.d).slice(0, REACH_OPPONENTS).map((x) => x.h);
      for (const h of [me, ...others]) {
        const before = position(data, col[h.p.id], now - 1) ?? h.xy!;
        const [vx, vy] = [h.xy![0] - before[0], h.xy![1] - before[1]];
        reach.push({ id: h.p.id, team: h.p.team, cx: h.xy![0] + REACH_A * vx,
                     cy: -(h.xy![1] + REACH_A * vy), main: h === me });
      }
    }
  }

  return (
    <svg className={`pitch view-${view}`} viewBox={`${-L / 2 - 2} ${-W / 2 - 2} ${L + 4} ${W + 4}`}
         role="img" aria-label="Replay of the synthetic match">
      <rect x={-L / 2 - 2} y={-W / 2 - 2} width={L + 4} height={W + 4} className="grass" />
      <Markings />
      {clip && clip.player && clip.player in col && (
        <Trail data={data} item={clip} now={now} j={col[clip.player]} />
      )}
      {reach.map((r) => (
        <g key={`reach-${r.id}`} className={`reach ${r.team}`}>
          <circle cx={r.cx} cy={r.cy} r={REACH_R} />
          {r.main && <text x={r.cx} y={r.cy - REACH_R - 0.6} className="reach-label">{reachLabel}</text>}
        </g>
      ))}
      {here.map(({ p, xy, s, i }) => {
        if (!xy) return null;
        const [x, y] = [xy[0], -xy[1]];
        const isSel = p.id === selected;
        const star = clip ? p.id === clip.player : inFocus(p.id);
        const dim = clip ? !star && !(clip.reach && reach.some((r) => r.id === p.id)) : false;
        const red = !clip && star && i !== null && s.red_zone[i] === 1;
        const since = clip || !star ? undefined
          : (peaks[p.id] ?? []).map((v) => now - v).find((d) => d >= 0 && d < PULSE_S);
        return (
          <g key={p.id} className={`player ${p.team}${isSel ? " sel" : ""}${dim ? " dim" : ""}`}
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
            {!clip && p.id === favourite && <circle cx={x} cy={y} r={2.0} className="fav" />}
            <circle cx={x} cy={y} r={1.45} className="dot" />
            <text x={x} y={y + 0.55} className="shirt">{p.shirt}</text>
            {!clip && mode === "fan" && i !== null && p.position !== "GK" && showBattery(p.id) && (
              <BatteryIcon pct={s.battery[i]} x={x} y={y - 3.6} />
            )}
          </g>
        );
      })}
      {ball && <circle cx={ball[0]} cy={-ball[1]} r={0.7} className="ball" />}
    </svg>
  );
}
