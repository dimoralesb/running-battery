import { useMemo } from "react";
import { type MatchData, type Mode, type Signals, fanLevel, position, signalIndex } from "./data";

// Pitch 105 × 68 m, centre origin (schema). y is drawn upwards.
const L = 105;
const W = 68;
const LOWEST = 5; // battery icons: selected, favourite and the five lowest (unless "all")
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
const REACH_WINDOW = 6; // shown from 6 s before to 6 s after a feed moment
const REACH_OPPONENTS = 2;

interface Props {
  data: MatchData;
  now: number;
  mode: Mode;
  selected: string | null;
  favourite: string | null;
  allBatteries: boolean;
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
    <div className="legend">
      <span><svg viewBox="-1.2 -1.2 2.4 2.4" className="key"><circle r={0.9} className="redzone-key" /></svg>
        Red-zone spell</span>
      <span><svg viewBox="-1.2 -1.2 2.4 2.4" className="key"><circle r={0.9} className="flat-key" /></svg>
        {text.legendFlatOut}</span>
      <span><svg viewBox="-1.2 -1.2 2.4 2.4" className="key"><circle r={0.9} className="reach-key" /></svg>
        {text.legendReach}</span>
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
        Favourite player</span>
    </div>
  );
}

export function Pitch({ data, now, mode, selected, favourite, allBatteries, reachLabel, flatLabel,
                        onSelect }: Props) {
  const { meta } = data;
  const ball = position(data, meta.ids.length, now);
  const peaks = useMemo(
    () => Object.fromEntries(Object.entries(data.signals).map(([id, s]) => [id, flatOutPeaks(s)])),
    [data],
  );
  const col = useMemo(() => Object.fromEntries(meta.players.map((p, j) => [p.id, j])), [meta]);

  // Where everyone is, and which batteries to draw.
  const here = meta.players.map((p, j) => {
    const xy = position(data, j, now);
    const s = data.signals[p.id];
    return { p, xy, s, i: xy ? signalIndex(s, now) : null };
  });
  const lowest = new Set(
    here.filter((h) => h.i !== null && h.p.position !== "GK")
      .sort((a, b) => a.s.battery[a.i!] - b.s.battery[b.i!])
      .slice(0, LOWEST).map((h) => h.p.id),
  );
  const showBattery = (id: string) =>
    allBatteries || id === selected || id === favourite || lowest.has(id);

  // Reachable areas around the nearest feed moment with a player (and his nearest opponents).
  const moment = data.feed.moments.find((m) => Math.abs(m.video_s - now) <= REACH_WINDOW
                                               && m.moment_id.split(":")[1] in col);
  const reach: { id: string; team: string; cx: number; cy: number; main: boolean }[] = [];
  if (moment) {
    const pid = moment.moment_id.split(":")[1];
    const me = here[col[pid]];
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
    <svg className="pitch" viewBox={`${-L / 2 - 2} ${-W / 2 - 2} ${L + 4} ${W + 4}`}
         role="img" aria-label="Replay of the synthetic match">
      <rect x={-L / 2 - 2} y={-W / 2 - 2} width={L + 4} height={W + 4} className="grass" />
      <Markings />
      {reach.map((r) => (
        <g key={`reach-${r.id}`} className={`reach ${r.team}`}>
          <circle cx={r.cx} cy={r.cy} r={REACH_R} />
          {r.main && <text x={r.cx} y={r.cy - REACH_R - 0.6} className="reach-label">{reachLabel}</text>}
        </g>
      ))}
      {here.map(({ p, xy, s, i }) => {
        if (!xy) return null;
        const [x, y] = [xy[0], -xy[1]];
        const red = i !== null && s.red_zone[i] === 1;
        const isSel = p.id === selected;
        const since = (peaks[p.id] ?? []).map((v) => now - v).find((d) => d >= 0 && d < PULSE_S);
        return (
          <g key={p.id} className={`player ${p.team}${isSel ? " sel" : ""}`}
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
            {p.id === favourite && <circle cx={x} cy={y} r={2.0} className="fav" />}
            <circle cx={x} cy={y} r={1.45} className="dot" />
            <text x={x} y={y + 0.55} className="shirt">{p.shirt}</text>
            {mode === "fan" && i !== null && p.position !== "GK" && showBattery(p.id) && (
              <BatteryIcon pct={s.battery[i]} x={x} y={y - 3.6} />
            )}
          </g>
        );
      })}
      {ball && <circle cx={ball[0]} cy={-ball[1]} r={0.7} className="ball" />}
    </svg>
  );
}
