import { useState } from "react";
import { type Entry, type Item, type MatchData, type Mode, clockLabel } from "./data";
import { Blocked, Verdict, splitSources } from "./Feed";

// The clip's details (decisions 29 and 34): shown when the clip is over, and growing with the
// run during the replay; the numbers, the run's speed second by second, the published
// number it is compared with, and the feed's lines with their sources and the Verifier's verdict.
const WIDTH = 640;
const HEIGHT = 170;
const PAD = { l: 40, r: 12, t: 26, b: 22 };
const HI = 5.5; // m/s, where high-speed running starts

interface Props {
  data: MatchData;
  item: Item;
  now: number;
  mode: Mode;
  name: string;
  replaying: boolean;
  band: string | null; // analyst: the battery's 10–90% band, as the first line
  text: Record<string, string>;
  onSeek: (v: number) => void;
}

const fill = (t: string, v: Record<string, string | number>) =>
  t.replace(/\{(\w+)\}/g, (_, k) => String(v[k] ?? ""));
const kmh = (v: number) => Math.round(v * 3.6);

/** Speed (m/s) per second of the clip, from the player's 1-s signals; null off the pitch. */
function speeds(d: MatchData, pid: string, a: number, b: number): (number | null)[] {
  const s = d.signals[pid];
  const out: (number | null)[] = [];
  for (let v = Math.floor(a); v <= b; v++) {
    const i = Math.floor(v - (s?.start ?? 0)); // a substitute's signals start mid-second
    out.push(s && i >= 0 && i < s.speed.length && s.speed[i] <= 110 ? s.speed[i] / 10 : null);
  }
  return out;
}

function Stats({ data, item, now, replaying, text }: Omit<Props, "mode" | "name" | "band" | "onSeek">) {
  const pid = item.player!;
  const a = item.lapse ? 0 : Math.floor(item.start - 3);
  const until = Math.min(now, item.end + 2);
  const v = speeds(data, pid, a, Math.max(until, a));
  const done = v.slice(0, Math.max(Math.floor(until) - a, 0));
  const dist = done.reduce<number>((t, x) => t + (x ?? 0), 0);
  const hsr = done.reduce<number>((t, x) => t + (x !== null && x > HI ? x : 0), 0);
  const cur = v[Math.floor(until) - a] ?? 0;
  const top = Math.max(cur, ...done.map((x) => x ?? 0)); // the second under way counts too
  const rows: [string, string, string?][] = item.lapse
    ? [[text.statDistanceMatch, `${(dist / 1000).toFixed(2)} km`]]
    : [
        ...(replaying ? [[text.statSpeedNow, `${cur.toFixed(1)} m/s`, `${kmh(cur)} km/h`] as [string, string, string]] : []),
        [text.statTop, `${top.toFixed(1)} m/s`, `${kmh(top)} km/h`],
        [text.statDistance, `${Math.round(dist)} m`],
        [text.statHsr, `${Math.round(hsr)} m`],
      ];
  if (item.kind === "back_to_back") {
    // Which run he is on, and the time since the last one ended (the gap timer).
    const segs = item.segments;
    const k = segs.filter(([s0]) => s0 <= now).length;
    const inRun = segs.some(([s0, s1]) => now >= s0 && now < s1);
    const prev = segs.filter(([, s1]) => s1 <= now).pop();
    rows.unshift([text.statRun, `${k} / ${segs.length}`]);
    if (!inRun && prev && k < segs.length) rows.unshift([text.statGap, `${Math.floor(now - prev[1])} s`]);
  }
  return (
    <dl className="stats">
      {rows.map(([k, x, sub]) => (
        <div key={k}><dt>{k}</dt><dd className="num">{x}{sub && <span className="unit"> ({sub})</span>}</dd></div>
      ))}
    </dl>
  );
}

/** The run's speed second by second (one series, so no legend: the title names it), or for
 * the most ground covered his distance since kick-off. */
function SpeedChart({ data, item, now, name, text, onSeek }: Omit<Props, "mode" | "replaying" | "band">) {
  const [hover, setHover] = useState<number | null>(null);
  const pid = item.player!;
  const a = item.lapse ? 0 : Math.floor(item.start - 3);
  const b = item.lapse ? Math.ceil(item.end) : Math.ceil(item.end + 2);
  const raw = speeds(data, pid, a, b);
  let run = 0;
  const values = item.lapse ? raw.map((x) => (run += x ?? 0) / 1000) : raw.map((x) => x ?? 0);
  const n = values.length;
  const max = item.lapse ? Math.ceil(Math.max(...values, 1)) : Math.max(10, Math.ceil(Math.max(...values)));
  const x = (i: number) => PAD.l + (i / Math.max(n - 1, 1)) * (WIDTH - PAD.l - PAD.r);
  const y = (v: number) => PAD.t + (1 - v / max) * (HEIGHT - PAD.t - PAD.b);
  const shown = Math.min(Math.max(Math.floor(now) - a, 0), n - 1);
  const d = values.slice(0, shown + 1).map((v, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join("");
  const fromEvent = (e: React.MouseEvent<SVGSVGElement>) => {
    const box = e.currentTarget.getBoundingClientRect();
    const i = Math.round((((e.clientX - box.left) / box.width) * WIDTH - PAD.l) / (WIDTH - PAD.l - PAD.r) * (n - 1));
    return i >= 0 && i <= shown ? i : null;
  };
  const ticks = item.lapse ? [0, Math.round(max / 2), max] : [0, 5, 10].filter((t) => t <= max);
  const unit = item.lapse ? " km" : "";
  return (
    <figure className="chart speed-chart">
      <figcaption>
        <strong>{fill(item.lapse ? text.distanceChart : text.speedChart, { name })}</strong>
        <span className="sub">{item.lapse ? text.distanceChartSub : text.speedChartSub}</span>
      </figcaption>
      <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} onMouseMove={(e) => setHover(fromEvent(e))}
           onMouseLeave={() => setHover(null)}
           onClick={(e) => { const i = fromEvent(e); if (i !== null) onSeek(a + i); }}>
        {!item.lapse && item.segments.map(([s0, s1]) => (
          <rect key={s0} x={x(Math.max(s0 - a, 0))} y={PAD.t}
                width={Math.max(x(Math.min(s1 - a, n - 1)) - x(Math.max(s0 - a, 0)), 1)}
                height={HEIGHT - PAD.t - PAD.b} className="zone run" />
        ))}
        {ticks.map((t) => (
          <g key={t}>
            <line x1={PAD.l} x2={WIDTH - PAD.r} y1={y(t)} y2={y(t)} className="grid" />
            <text x={PAD.l - 6} y={y(t) + 4} className="axis" textAnchor="end">{t}{unit}</text>
          </g>
        ))}
        <text x={4} y={12} className="axis axis-title">{item.lapse ? text.distanceAxis : text.speedAxis}</text>
        {!item.lapse && (
          <line x1={PAD.l} x2={WIDTH - PAD.r} y1={y(HI)} y2={y(HI)} className="threshold" />
        )}
        {[0, Math.floor((n - 1) / 2), n - 1].map((i) => (
          <text key={i} x={x(i)} y={HEIGHT - 6} className="axis"
                textAnchor={i === 0 ? "start" : i === n - 1 ? "end" : "middle"}>
            {clockLabel(data.meta, a + i)}
          </text>
        ))}
        <path d={d} className={`line ${item.team}`} />
        <line x1={x(shown)} x2={x(shown)} y1={PAD.t} y2={HEIGHT - PAD.b} className="now" />
        {hover !== null && (
          <g>
            <line x1={x(hover)} x2={x(hover)} y1={PAD.t} y2={HEIGHT - PAD.b} className="cross" />
            <circle cx={x(hover)} cy={y(values[hover])} r={4} className={`marker ${item.team}`} />
          </g>
        )}
      </svg>
      <div className="tooltip" aria-live="polite">
        {hover !== null ? (
          <>
            <strong>{clockLabel(data.meta, a + hover)}</strong>
            <span>{item.lapse ? `${values[hover].toFixed(2)} km`
              : `${values[hover].toFixed(1)} m/s (${kmh(values[hover])} km/h)`}</span>
          </>
        ) : (
          <span className="sub">{text.chartHint}</span>
        )}
      </div>
    </figure>
  );
}

const COMPARE: Record<string, [string, string, string]> = {
  // kind: [his fact, the published fact, its label in copy.json]
  top_speed: ["top_speed", "published_match_top_speed_for_position", "cmpTopSpeed"],
  longest_run: ["metres", "typical_run", "cmpRun"],
  recovery_run: ["metres", "typical_run", "cmpRun"],
  back_to_back: ["longest_gap", "usual_gap_for_position", "cmpGap"],
  busiest_minute: ["metres_in_one_minute", "published_best_minute", "cmpMinute"],
  most_ground: ["km", "published_for_position", "cmpGround"],
};

/** His number against the published one, on one scale (shown once the clip is over). */
function Compare({ item, name, text }: { item: Item; name: string; text: Record<string, string> }) {
  const row = item.h ? COMPARE[item.h.kind] : undefined;
  if (!row || !item.h) return null;
  const f = item.h.facts;
  const [his, pub] = [f[row[0]], f[row[1]]];
  if (typeof his !== "object" || typeof pub !== "object") return null;
  const unit = his.unit.split(/[ ,]/)[0];
  const max = Math.max(his.value, pub.value) || 1;
  const bars: [string, number, string][] = [
    [name, his.value, item.team],
    [text[row[2]], pub.value, "published"],
  ];
  return (
    <figure className="compare">
      <figcaption><strong>{text.compare}</strong></figcaption>
      {bars.map(([label, v, cls]) => (
        <div key={label} className="cmp-row">
          <span className="cmp-label">{label}</span>
          <span className="cmp-track"><span className={`cmp-bar ${cls}`} style={{ width: `${(100 * v) / max}%` }} /></span>
          <span className="cmp-value num">{v} {unit}</span>
        </div>
      ))}
      <p className="sub">{pub.source}</p>
    </figure>
  );
}

function Line({ e, mode, text }: { e: Entry; mode: Mode; text: Record<string, string> }) {
  return (
    <article className={`line${e.verdict === "blocked" ? " blocked" : ""}`}>
      {e.verdict === "blocked" ? <Blocked e={e} text={text} /> : <p>{e.sentence}</p>}
      {e.verdict !== "blocked" && <Verdict e={e} mode={mode} text={text} />}
    </article>
  );
}

export function Replay({ data, item, now, mode, name, replaying, band, text, onSeek }: Props) {
  const lines = item.momentId
    ? data.feed.entries.filter((e) => e.moment_id === item.momentId && e.mode === mode && e.shown)
    : [];
  const blocked = item.momentId
    ? data.feed.entries.filter((e) => e.moment_id === item.momentId && e.mode === mode
                                      && e.verdict === "blocked")
    : [];
  const over = now >= item.end;
  const about = item.momentKind ? text[`about_${item.momentKind}`] : undefined;
  const [cites, fields] = item.h ? splitSources(item.h.sources) : [[], []];
  return (
    <section className="replay">
      {item.player && <Stats data={data} item={item} now={now} replaying={replaying} text={text} />}
      <h3>{text.linesTitle}</h3>
      {[
        band && <article key="band" className="line"><p>{band}</p></article>,
        item.h && (
          <article key="caption" className="line">
            <p>{item.caption}</p>
            <details className="verdict" open={mode === "analyst"}>
              <summary>{mode === "analyst" ? `${text.hlChecked} · ${text.measuredFact}` : text.verdictMeasured}</summary>
              <ul>
                {cites.length > 0 && <li>{cites.join(", ")}</li>}
                {fields.map((f) => <li key={f}><code>{f}</code></li>)}
              </ul>
            </details>
          </article>
        ),
        ...lines.map((e, k) => <Line key={k} e={e} mode={mode} text={text} />),
      ].filter(Boolean).flatMap((el, k) =>
        // What this kind of moment is, after the clip's first line (decision 38): the first
        // line stays above the fold at 1440×900 (JOURNEY fix 1).
        k === 0 && about ? [el, <p key="about" className="sub about">{about}</p>] : [el])}
      {blocked.length > 0 && (
        <>
          <h4>{text.verdictBlocked}</h4>
          {blocked.map((e, k) => <Line key={k} e={e} mode={mode} text={text} />)}
        </>
      )}
      {item.player && <SpeedChart data={data} item={item} now={now} name={name} text={text} onSeek={onSeek} />}
      {over && <Compare item={item} name={name} text={text} />}
    </section>
  );
}
