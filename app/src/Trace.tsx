import { useState } from "react";
import { type Meta, type Signals, clockLabel } from "./data";

// Two charts on one time axis (never two y-scales on one chart): the battery for a typical
// professional with its 10–90% band, and high-speed running in the last minute.
const WIDTH = 640;
const PAD = { l: 40, r: 12, t: 24, b: 22 };

interface Props {
  signals: Signals;
  meta: Meta;
  now: number;
  name: string;
  text: Record<string, string>;
  onSeek: (v: number) => void;
}

function path(values: number[], x: (i: number) => number, y: (v: number) => number): string {
  let d = "";
  values.forEach((v, i) => {
    d += `${i ? "L" : "M"}${x(i).toFixed(1)},${y(v).toFixed(1)}`;
  });
  return d;
}

function Chart({ s, meta, now, height, values, max, unit, title, yTitle, band, hover, setHover,
                 onSeek }: {
  s: Signals; meta: Meta; now: number; height: number; values: number[]; max: number;
  unit: string; title: string; yTitle: string; band?: [number[], number[]]; hover: number | null;
  setHover: (i: number | null) => void; onSeek: (v: number) => void;
}) {
  const n = values.length;
  const x = (i: number) => PAD.l + (i / Math.max(n - 1, 1)) * (WIDTH - PAD.l - PAD.r);
  const y = (v: number) => PAD.t + (1 - v / max) * (height - PAD.t - PAD.b);
  const ticks = [0, max / 2, max];
  const cursor = now - s.start;
  const half = meta.periods.find((p) => p.period === 2)?.video_start ?? null;
  const red: [number, number][] = [];
  s.red_zone.forEach((r, i) => {
    if (r && (i === 0 || !s.red_zone[i - 1])) red.push([i, i]);
    if (r) red[red.length - 1][1] = i;
  });
  const fromEvent = (e: React.MouseEvent<SVGSVGElement>) => {
    const box = e.currentTarget.getBoundingClientRect();
    const px = ((e.clientX - box.left) / box.width) * WIDTH;
    const i = Math.round(((px - PAD.l) / (WIDTH - PAD.l - PAD.r)) * (n - 1));
    return i >= 0 && i < n ? i : null;
  };
  // Ticks on the broadcast clock: 0, 15, 30 (first half), 45, 60, 75, 90 (second half).
  const xTicks: [number, string][] = [];
  for (const c of [0, 900, 1800, 2700, 3600, 4500, 5400]) {
    const v = c < 2700 || half === null ? c : half + c - 2700;
    if (v - s.start >= 0 && v - s.start < n) xTicks.push([v - s.start, `${c / 60}:00`]);
  }
  return (
    <figure className="chart">
      <figcaption>{title}</figcaption>
      <svg viewBox={`0 0 ${WIDTH} ${height}`} onMouseMove={(e) => setHover(fromEvent(e))}
           onMouseLeave={() => setHover(null)}
           onClick={(e) => { const i = fromEvent(e); if (i !== null) onSeek(s.start + i); }}>
        {red.map(([a, b]) => (
          <rect key={a} x={x(a)} y={PAD.t} width={Math.max(x(b) - x(a), 1)}
                height={height - PAD.t - PAD.b} className="zone" />
        ))}
        {ticks.map((t) => (
          <g key={t}>
            <line x1={PAD.l} x2={WIDTH - PAD.r} y1={y(t)} y2={y(t)} className="grid" />
            <text x={PAD.l - 6} y={y(t) + 4} className="axis" textAnchor="end">{t}{unit}</text>
          </g>
        ))}
        <text x={4} y={12} className="axis axis-title">{yTitle}</text>
        {xTicks.map(([k, label]) => (
          <text key={k} x={x(k)} y={height - 6} className="axis" textAnchor="middle">
            {label}
          </text>
        ))}
        {half !== null && half > s.start && half < s.start + n && (
          <line x1={x(half - s.start)} x2={x(half - s.start)} y1={PAD.t} y2={height - PAD.b}
                className="half" />
        )}
        {band && (
          <path className="band"
                d={`${path(band[1], x, y)}L${[...band[0]].reverse().map((v, k) =>
                  `${x(n - 1 - k).toFixed(1)},${y(v).toFixed(1)}`).join("L")}Z`} />
        )}
        <path d={path(values, x, y)} className="line" />
        {cursor >= 0 && cursor < n && (
          <line x1={x(cursor)} x2={x(cursor)} y1={PAD.t} y2={height - PAD.b} className="now" />
        )}
        {hover !== null && (
          <g>
            <line x1={x(hover)} x2={x(hover)} y1={PAD.t} y2={height - PAD.b} className="cross" />
            <circle cx={x(hover)} cy={y(values[hover])} r={4} className="marker" />
          </g>
        )}
      </svg>
    </figure>
  );
}

export function Trace({ signals: s, meta, now, name, text, onSeek }: Props) {
  const [hover, setHover] = useState<number | null>(null);
  const band = s.lo && s.hi ? ([s.lo, s.hi] as [number[], number[]]) : undefined;
  const maxHsr = Math.max(80, Math.ceil(Math.max(...s.hsr_1min) / 20) * 20);
  const h = hover;
  return (
    <div className="trace">
      <Chart s={s} meta={meta} now={now} height={170} values={s.battery} max={100} unit="%"
             title={text.traceBattery.replace("{name}", name)} yTitle={text.traceBatteryAxis}
             band={band} hover={hover} setHover={setHover} onSeek={onSeek} />
      <Chart s={s} meta={meta} now={now} height={120} values={s.hsr_1min} max={maxHsr}
             unit=" m" title={text.traceHsr.replace("{name}", name)} yTitle={text.traceHsrAxis}
             hover={hover} setHover={setHover} onSeek={onSeek} />
      <div className="tooltip" aria-live="polite">
        {h !== null ? (
          <>
            <strong>{clockLabel(meta, s.start + h)}</strong>
            <span>battery {s.battery[h]}%{band ? ` (${s.lo![h]}–${s.hi![h]}%)` : ""}</span>
            {s.low_chance && <span>typical-pro chance {s.low_chance[h]}%</span>}
            <span>{s.hsr_1min[h]} m in the last minute</span>
            {s.red_zone[h] ? <span>red-zone spell</span> : null}
          </>
        ) : (
          <span className="muted">Hover a chart for values; click to jump there. Shaded:
            red-zone spells. Dashed: half-time.</span>
        )}
      </div>
    </div>
  );
}
