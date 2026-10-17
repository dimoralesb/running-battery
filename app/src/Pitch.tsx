import { type MatchData, type Mode, fanLevel, position, signalIndex } from "./data";

// Pitch 105 × 68 m, centre origin (schema). y is drawn upwards.
const L = 105;
const W = 68;

interface Props {
  data: MatchData;
  now: number;
  mode: Mode;
  selected: string | null;
  favourite: string | null;
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

export function Legend({ mode, batteryText }: { mode: Mode; batteryText: string }) {
  return (
    <div className="legend">
      <span><svg viewBox="-1.2 -1.2 2.4 2.4" className="key"><circle r={0.9} className="redzone-key" /></svg>
        Red-zone spell</span>
      {mode === "fan" && (
        <span><svg viewBox="-3 -0.4 6 1.8" className="key wide"><BatteryIcon pct={60} x={0} y={0} /></svg>
          {batteryText}</span>
      )}
      <span><svg viewBox="-1.2 -1.2 2.4 2.4" className="key"><circle r={0.8} className="fav-key" /></svg>
        Favourite player</span>
    </div>
  );
}

export function Pitch({ data, now, mode, selected, favourite, onSelect }: Props) {
  const { meta } = data;
  const ball = position(data, meta.ids.length, now);
  return (
    <svg className="pitch" viewBox={`${-L / 2 - 2} ${-W / 2 - 2} ${L + 4} ${W + 4}`}
         role="img" aria-label="Replay of the synthetic match">
      <rect x={-L / 2 - 2} y={-W / 2 - 2} width={L + 4} height={W + 4} className="grass" />
      <Markings />
      {meta.players.map((p, j) => {
        const xy = position(data, j, now);
        if (!xy) return null;
        const [x, y] = [xy[0], -xy[1]];
        const s = data.signals[p.id];
        const i = signalIndex(s, now);
        const red = i !== null && s.red_zone[i] === 1;
        const isSel = p.id === selected;
        return (
          <g key={p.id} className={`player ${p.team}${isSel ? " sel" : ""}`}
             onClick={() => onSelect(p.id)} role="button" aria-label={`${p.shirt} ${p.name}`}>
            <circle cx={x} cy={y} r={3} className="hit" />
            {red && <circle cx={x} cy={y} r={2.3} className="redzone" />}
            {p.id === favourite && <circle cx={x} cy={y} r={2.0} className="fav" />}
            <circle cx={x} cy={y} r={1.45} className="dot" />
            <text x={x} y={y + 0.55} className="shirt">{p.shirt}</text>
            {mode === "fan" && i !== null && p.position !== "GK" && (
              <BatteryIcon pct={s.battery[i]} x={x} y={y - 3.6} />
            )}
          </g>
        );
      })}
      {ball && <circle cx={ball[0]} cy={-ball[1]} r={0.7} className="ball" />}
    </svg>
  );
}
