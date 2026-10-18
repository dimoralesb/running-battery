import { useState } from "react";
import { type Meta } from "./data";

// Who's doing the running (synthesis §9.1 idea 8, first called "tug of war"): both teams' high-speed running per ball-in-play minute
// in 5-min blocks, drawn as the blocks finish. Two series on one axis: a legend plus direct
// labels at the line ends.
const WIDTH = 640;
const HEIGHT = 170;
const PAD = { l: 44, r: 96, t: 26, b: 22 };

interface Props {
  meta: Meta;
  now: number;
  title: string;
  sub: string;
  yTitle: string;
  onSeek: (v: number) => void;
}

export function TeamChart({ meta, now, title, sub, yTitle, onSeek }: Props) {
  const [hover, setHover] = useState<number | null>(null);
  const blocks = meta.team_running;
  const end = blocks.length ? blocks[blocks.length - 1].video_end : 1;
  const done = blocks.filter((b) => b.video_end <= now + 0.5);
  const all = blocks.flatMap((b) => [b.home.hsr ?? 0, b.away.hsr ?? 0]);
  const max = Math.max(50, Math.ceil(Math.max(...all) / 50) * 50);
  const x = (v: number) => PAD.l + (v / end) * (WIDTH - PAD.l - PAD.r);
  const y = (v: number) => PAD.t + (1 - v / max) * (HEIGHT - PAD.t - PAD.b);
  const mid = (b: (typeof blocks)[number]) => (b.video_start + b.video_end) / 2;
  const line = (team: "home" | "away") =>
    done.filter((b) => b[team].hsr !== null)
      .map((b, k) => `${k ? "L" : "M"}${x(mid(b)).toFixed(1)},${y(b[team].hsr!).toFixed(1)}`)
      .join("");
  const half = meta.periods.find((p) => p.period === 2)?.video_start;
  const [home, away] = meta.teams;
  const last = done[done.length - 1];
  const h = hover !== null ? done[hover] : null;
  const fromEvent = (e: React.MouseEvent<SVGSVGElement>) => {
    const box = e.currentTarget.getBoundingClientRect();
    const v = (((e.clientX - box.left) / box.width) * WIDTH - PAD.l) / (WIDTH - PAD.l - PAD.r) * end;
    let best: number | null = null;
    done.forEach((b, k) => {
      if (best === null || Math.abs(mid(b) - v) < Math.abs(mid(done[best]) - v)) best = k;
    });
    return best;
  };
  return (
    <figure className="chart team-chart card">
      <figcaption><strong>{title}</strong><span className="sub">{sub}</span></figcaption>
      <div className="legend">
        <span><i className="swatch home" />{home.name}</span>
        <span><i className="swatch away" />{away.name}</span>
      </div>
      <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} onMouseMove={(e) => setHover(fromEvent(e))}
           onMouseLeave={() => setHover(null)}
           onClick={(e) => { const k = fromEvent(e); if (k !== null) onSeek(done[k].video_end); }}>
        {[0, max / 2, max].map((t) => (
          <g key={t}>
            <line x1={PAD.l} x2={WIDTH - PAD.r} y1={y(t)} y2={y(t)} className="grid" />
            <text x={PAD.l - 6} y={y(t) + 4} className="axis" textAnchor="end">{t}</text>
          </g>
        ))}
        <text x={PAD.l - 6} y={12} className="axis axis-title" textAnchor="start"
              transform={`translate(${-(PAD.l - 6) + 4} 0)`}>{yTitle}</text>
        {[0, 900, 1800].map((c) => (
          <text key={c} x={x(c)} y={HEIGHT - 6} className="axis" textAnchor="middle">{c / 60}:00</text>
        ))}
        {half !== undefined && (
          <>
            <line x1={x(half)} x2={x(half)} y1={PAD.t} y2={HEIGHT - PAD.b} className="half" />
            {[2700, 3600, 4500].map((c) => (
              <text key={c} x={x(half + c - 2700)} y={HEIGHT - 6} className="axis"
                    textAnchor="middle">{c / 60}:00</text>
            ))}
          </>
        )}
        <path d={line("home")} className="team-line home" />
        <path d={line("away")} className="team-line away" />
        {last && last.home.hsr !== null && last.away.hsr !== null && (() => {
          // Direct labels at the line ends, at least 13 px apart.
          let yh = y(last.home.hsr) + 4;
          let ya = y(last.away.hsr) + 4;
          if (Math.abs(yh - ya) < 13) {
            const c = (yh + ya) / 2;
            const up = last.home.hsr >= last.away.hsr;
            yh = c + (up ? -6.5 : 6.5);
            ya = c + (up ? 6.5 : -6.5);
          }
          return (
            <>
              <text x={x(mid(last)) + 6} y={yh} className="direct">{home.name}</text>
              <text x={x(mid(last)) + 6} y={ya} className="direct">{away.name}</text>
            </>
          );
        })()}
        {x(Math.min(now, end)) > PAD.l && (
          <line x1={x(Math.min(now, end))} x2={x(Math.min(now, end))} y1={PAD.t}
                y2={HEIGHT - PAD.b} className="now" />
        )}
        {h && (
          <g>
            <line x1={x(mid(h))} x2={x(mid(h))} y1={PAD.t} y2={HEIGHT - PAD.b} className="cross" />
            {h.home.hsr !== null && <circle cx={x(mid(h))} cy={y(h.home.hsr)} r={4} className="marker home" />}
            {h.away.hsr !== null && <circle cx={x(mid(h))} cy={y(h.away.hsr)} r={4} className="marker away" />}
          </g>
        )}
      </svg>
      <div className="tooltip" aria-live="polite">
        {h ? (
          <>
            <strong>from {h.clock}</strong>
            <span>{home.name} {h.home.hsr ?? "–"} m a minute</span>
            <span>{away.name} {h.away.hsr ?? "–"} m a minute</span>
            <span className="muted">ball in play {Math.round(h.home.in_play_s / 60)} min</span>
          </>
        ) : (
          <span className="muted">Hover for values; click to jump there. Dashed: half-time.</span>
        )}
      </div>
    </figure>
  );
}
