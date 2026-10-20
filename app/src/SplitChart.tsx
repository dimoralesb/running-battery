import { useState } from "react";
import { type Meta, type SituationBlock } from "./data";

// Where the running happened (decision 30): each team's high-speed running per minute of each
// situation of play (G5), from possession and the ball's position only. One bar per team and
// situation on one scale, values at the tips; hover a bar for its share and minutes. The
// situations say where the running happened, never why (claims 38, 39).

interface Props {
  meta: Meta;
  blocks: SituationBlock[]; // the 15-min blocks to add up
  scope: string; // "Finished 15-minute blocks so far." or "In 0:00–15:00."
  text: Record<string, string>;
}

const fill = (t: string, v: Record<string, string | number>) =>
  t.replace(/\{(\w+)\}/g, (_, k) => String(v[k] ?? ""));
const CHANGED = ["after_losing", "after_winning"];
const MIN_S = 30; // a rate needs 30 s of ball in play in that situation (our assumption)

/** Metres and ball-in-play seconds per situation for one team, summed over the blocks. */
function totals(meta: Meta, blocks: SituationBlock[], team: string) {
  const out: Record<string, [number, number]> = {};
  for (const k of meta.situations) out[k] = [0, 0];
  for (const b of blocks) {
    const x = b[team] as Record<string, [number, number]>;
    for (const k of meta.situations) {
      out[k][0] += x[k][0];
      out[k][1] += x[k][1];
    }
  }
  return out;
}

export function SplitChart({ meta, blocks, scope, text }: Props) {
  const [hover, setHover] = useState<[string, string] | null>(null);
  const teams = meta.teams;
  const t = Object.fromEntries(teams.map((x) => [x.id, totals(meta, blocks, x.id)]));
  const rate = (team: string, k: string) => {
    const [m, s] = t[team][k];
    return s >= MIN_S ? (m / s) * 60 : null;
  };
  const sum = (team: string, i: 0 | 1, keys = meta.situations) =>
    keys.reduce((a, k) => a + t[team][k][i], 0);
  const pct = (part: number, whole: number) => (whole > 0 ? Math.round((100 * part) / whole) : 0);
  const max = Math.max(1, ...teams.flatMap((x) => meta.situations.map((k) => rate(x.id, k) ?? 0)));
  const name = (team: string) => teams.find((x) => x.id === team)?.name ?? team;
  const empty = !blocks.length || teams.every((x) => sum(x.id, 1) === 0);
  return (
    <figure className="chart split-chart">
      <figcaption>
        <strong>{text.splitChart}</strong>
        <span className="sub">{text.splitChartSub} {scope}</span>
      </figcaption>
      <div className="legend">
        {teams.map((x) => <span key={x.id}><i className={`swatch ${x.id}`} />{x.name}</span>)}
        <span className="muted">{text.splitAxis}</span>
      </div>
      {empty ? (
        <p className="muted small">{text.hlNone}</p>
      ) : (
        <div className="split-rows" onMouseLeave={() => setHover(null)}>
          {meta.situations.map((k) => (
            <div key={k} className="split-row">
              <span className="split-label">
                {text[`sit_${k}`] ?? k}
                <span className="small muted">
                  {teams.map((x) => (t[x.id][k][1] / 60).toFixed(1)).join(" / ")} min
                </span>
              </span>
              <div className="split-bars">
                {teams.map((x) => {
                  const r = rate(x.id, k);
                  const on = hover !== null && hover[0] === k && hover[1] === x.id;
                  return (
                    <div key={x.id} className={`split-bar${on ? " on" : ""}`}
                         onMouseEnter={() => setHover([k, x.id])}
                         onFocus={() => setHover([k, x.id])} tabIndex={0}
                         aria-label={`${x.name}: ${r === null ? "–" : Math.round(r)} m a minute`}>
                      <span className="cmp-track">
                        <span className={`cmp-bar ${x.id}`}
                              style={{ width: `${(100 * (r ?? 0)) / max}%` }} />
                      </span>
                      <span className="cmp-value">{r === null ? "–" : Math.round(r)}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      )}
      {!empty && (
        <div className="tooltip split-tip" aria-live="polite">
          {hover ? (
            <span>{fill(text.splitHover, {
              team: name(hover[1]), situation: text[`sit_${hover[0]}`] ?? hover[0],
              rate: rate(hover[1], hover[0]) === null ? "–" : Math.round(rate(hover[1], hover[0])!),
              share: pct(t[hover[1]][hover[0]][0], sum(hover[1], 0)),
              time: pct(t[hover[1]][hover[0]][1], sum(hover[1], 1)),
            })}</span>
          ) : (
            teams.map((x) => (
              <span key={x.id}>{fill(text.splitShare, {
                team: x.name, share: pct(sum(x.id, 0, CHANGED), sum(x.id, 0)),
                time: pct(sum(x.id, 1, CHANGED), sum(x.id, 1)),
              })}</span>
            ))
          )}
        </div>
      )}
    </figure>
  );
}
