import { useState } from "react";
import { type MatchData, clockLabel, signalIndex } from "./data";

// Every outfield player's battery, minute by minute (decision 64): one row per player in each team
// (starters, then substitutes in the order they came on), one column per minute of play, read at
// the minute's last second. One hue, stronger where the battery is lower; a player off the pitch
// has no square. A readout line under it gives the square under the pointer.

const CELL = 7;
const GAP = 1;
const LABEL = 92;
const ROW = 12;
const HALF_GAP = 8;
const FLOOR = 40; // the strongest colour: a typical pro at 40% or lower

interface Props {
  data: MatchData;
  text: Record<string, string>;
}

const fill = (t: string, v: Record<string, string | number>) =>
  t.replace(/\{(\w+)\}/g, (_, k) => String(v[k] ?? ""));

export function BatteryMap({ data, text }: Props) {
  const [hover, setHover] = useState<{ name: string; v: number; pct: number } | null>(null);
  const { meta } = data;
  // Each column: the video second it is read at, and its half.
  const cols = meta.periods.flatMap((p, h) =>
    Array.from({ length: Math.ceil(p.duration_s / 60) }, (_, m) => ({
      v: p.video_start + Math.min((m + 1) * 60, p.duration_s) - 1, h, start: p.video_start + m * 60 })));
  const colX = (j: number) => LABEL + j * (CELL + GAP) + (cols[j].h ? HALF_GAP : 0);
  const width = colX(cols.length - 1) + CELL + 24;
  const teams = meta.teams.map((t) => {
    const players = meta.players.filter((p) => p.team === t.id && p.position !== "GK" && data.signals[p.id]);
    const first = (id: string) => data.signals[id]?.start ?? 0;
    players.sort((a, b) => Number(b.starter) - Number(a.starter) || first(a.id) - first(b.id));
    return { team: t, players };
  });
  const surname = (n: string) => n.split(" ").slice(-1)[0];
  let y = 0;
  const rows: JSX.Element[] = [];
  for (const { team, players } of teams) {
    rows.push(<text key={team.id} x={0} y={y + 10} className="map-team">{team.name}</text>);
    y += ROW + 4;
    for (const p of players) {
      const s = data.signals[p.id];
      const top = y;
      rows.push(
        <g key={p.id}>
          <text x={LABEL - 6} y={top + CELL} className="axis" textAnchor="end">{`${p.shirt} ${surname(p.name)}`}</text>
          {cols.map((c, j) => {
            const i = signalIndex(s, c.v);
            if (i === null || c.v < s.start) return null;
            const pct = s.battery[i];
            const strength = Math.min(Math.max((100 - pct) / (100 - FLOOR), 0.1), 1);
            return (
              <rect key={j} x={colX(j)} y={top} width={CELL} height={CELL + 2} rx={1}
                    className="map-cell" fillOpacity={strength}
                    onMouseEnter={() => setHover({ name: p.name, v: c.v, pct })} />
            );
          })}
        </g>,
      );
      y += ROW;
    }
    y += 10;
  }
  // Ticks every 15 minutes of each half, none in added time.
  const ticks = cols.map((c, j) => ({ c, j })).filter(({ c }) => {
    const m = Math.round((c.start - meta.periods[c.h].video_start) / 60);
    return m % 15 === 0 && m < 45;
  });
  return (
    <figure className="chart battery-map">
      <figcaption>
        <strong>{text.mapTitle}</strong>
        <span className="sub">{text.mapSub}</span>
      </figcaption>
      <div className="map-legend" aria-hidden="true">
        <span>{text.mapHigh}</span><span className="map-ramp" /><span>{text.mapLow}</span>
      </div>
      <div className="map-scroll">
        <svg viewBox={`0 0 ${width} ${y + 14}`} style={{ minWidth: width }} role="img" aria-label={text.mapTitle}
             onMouseLeave={() => setHover(null)}>
          {rows}
          {ticks.map(({ c, j }) => (
            <text key={j} x={colX(j)} y={y + 10} className="axis">{clockLabel(meta, c.start)}</text>
          ))}
        </svg>
      </div>
      <p className="readout" aria-live="polite">
        {hover ? fill(text.mapHover, { name: hover.name, time: clockLabel(meta, hover.v), pct: hover.pct })
          : text.mapHint}
      </p>
    </figure>
  );
}
