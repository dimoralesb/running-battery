import { useState } from "react";
import { type Item, type MatchData, type Signals, clockLabel, signalIndex, signalTime } from "./data";

// "How it works" (decision 52): the third view, in plain words with the technical names in one
// quiet line per part (decisions 53–54), all from the README and checked by the Verifier's copy
// test (copy.json "how*"). The battery chart uses the opening clip's player around his run, from
// this match's own data, and shades the seconds above critical speed so the drain and the refill
// show (with wear, decision 56: in the story match 35 of his 35 seconds above it that change the
// battery lower it). Decision 60: the check's test results are gone, and the page cites its
// research with [n] markers and a References section (copy.json "howRef_<group>_<n>", each ending
// in its DOI link).

const REPO = "https://github.com/dimoralesb/running-battery#readme";
const CS_KMH = 4.1 * 3.6; // the typical pro's critical speed, 4.1 m/s (engine prior, PLAN decision 13)
const WIDTH = 640;
const PAD = { l: 40, r: 12, t: 22, b: 22 };

interface Props {
  data: MatchData;
  item: Item | undefined; // the opening clip: its player and run
  name: string;
  text: Record<string, string>;
}

const fill = (t: string, v: Record<string, string | number>) =>
  t.replace(/\{(\w+)\}/g, (_, k) => String(v[k] ?? ""));

/** The [n] citation markers, set apart so the sentence reads first; they don't link anywhere. */
const cite = (t: string) =>
  t.split(/(\[\d[\d,\s–]*\])/).map((part, k) => (k % 2 ? <span key={k} className="cite">{part}</span> : part));

/** His speed and the typical-pro battery, second by second, from 90 s before the clip's run to
 * 8 minutes after it, within its half (the story match's 3:50 run takes the battery from 90% to
 * 58%, back to 83% by 11:30, with wear); both panels shade his seconds above critical speed. */
function BatteryChart({ data, item, name, text }: Props & { item: Item }) {
  const s = data.signals[item.player!];
  const half = data.meta.periods.filter((p) => p.video_start <= item.start).at(-1) ?? data.meta.periods[0];
  const a = Math.floor(Math.max(item.start - 90, half.video_start));
  const b = Math.ceil(Math.min(item.end + 480, half.video_start + half.duration_s - 1));
  const speed: (number | null)[] = [];
  const battery: (number | null)[] = [];
  for (let v = a; v <= b; v++) {
    const i = signalIndex(s, v);
    speed.push(i !== null && s.speed[i] <= 110 ? (s.speed[i] / 10) * 3.6 : null); // km/h, as the text
    battery.push(i !== null ? s.battery[i] : null);
  }
  const n = speed.length;
  // His spells above critical speed, as [first, last] second indices.
  const above: [number, number][] = [];
  speed.forEach((v, k) => {
    if (v === null || v <= CS_KMH) return;
    const last = above[above.length - 1];
    if (last && last[1] === k - 1) last[1] = k;
    else above.push([k, k]);
  });
  const x = (k: number) => PAD.l + (k / Math.max(n - 1, 1)) * (WIDTH - PAD.l - PAD.r);
  const path = (vs: (number | null)[], y: (v: number) => number) =>
    vs.map((v, k) => (v === null ? "" : `${k && vs[k - 1] !== null ? "L" : "M"}${x(k).toFixed(1)},${y(v).toFixed(1)}`)).join("");
  const panel = (h: number, max: number, ticks: number[], title: string, vs: (number | null)[], extra?: number) => {
    const y = (v: number) => PAD.t + (1 - v / max) * (h - PAD.t - PAD.b);
    return (
      <svg viewBox={`0 0 ${WIDTH} ${h}`} role="img" aria-label={title}>
        {ticks.map((t) => (
          <g key={t}>
            <line x1={PAD.l} x2={WIDTH - PAD.r} y1={y(t)} y2={y(t)} className="grid" />
            <text x={PAD.l - 6} y={y(t) + 4} className="axis" textAnchor="end">{t}</text>
          </g>
        ))}
        <text x={4} y={12} className="axis axis-title">{title}</text>
        {extra !== undefined && (
          <line x1={PAD.l} x2={WIDTH - PAD.r} y1={y(extra)} y2={y(extra)} className="threshold" />
        )}
        {above.map(([k0, k1]) => (
          <rect key={k0} x={x(k0)} y={PAD.t} width={Math.max(x(k1 + 1) - x(k0), 1.5)}
                height={h - PAD.t - PAD.b} className="zone" />
        ))}
        <path d={path(vs, y)} className={`line ${item.team}`} />
        {[0, Math.floor((n - 1) / 2), n - 1].map((k) => (
          <text key={k} x={x(k)} y={h - 6} className="axis"
                textAnchor={k === 0 ? "start" : k === n - 1 ? "end" : "middle"}>{clockLabel(data.meta, a + k)}</text>
        ))}
      </svg>
    );
  };
  return (
    <figure className="chart speed-chart how-chart">
      <figcaption>
        <strong>{fill(text.howChartTitle, { name })}</strong>
        <span className="sub">{text.howChartSub}</span>
      </figcaption>
      {panel(150, 36, [0, 15, 30], text.howChartSpeed, speed, CS_KMH)}
      {panel(130, 100, [0, 50, 100], text.howChartBattery, battery)}
    </figure>
  );
}

// Decision 64: two charts from the same player's whole match. The first draws the battery three
// ways for one typical pro (CS 4.1 m/s, D′ 180 m): the standard model (k 1, engine/params.py), our
// slower refill (k 4) and ours with wear (α 1, 400 m, half kept at half-time), one step a second
// from the exported speeds; the last stays within about 2 points of the page's battery, which is
// the middle of 200 weighted typical pros. The second is his best average speed over each length
// of time, against the typical pro's critical speed (Mizelman2024; Lord2020).
const D_PRIME = 180;
const HALF_TIME_S = 900;
type Variant = { k: number; wear: boolean };
const VARIANTS: Variant[] = [{ k: 1, wear: false }, { k: 4, wear: false }, { k: 4, wear: true }];

/** One typical pro's battery (%) for each second of a player's signals. */
function typicalBattery(s: Signals, { k, wear }: Variant): number[] {
  const cs = CS_KMH / 3.6;
  const tau = (v: number) => Math.min(Math.max((k * D_PRIME) / Math.max(cs - v, 1e-9), 30), 900);
  const second = s.halves?.[1]?.[1] ?? -1;
  let b = D_PRIME;
  let w = 0;
  return s.speed.map((raw, i) => {
    if (i === second) {
      b = D_PRIME - (D_PRIME - b) * Math.exp(-HALF_TIME_S / tau(0));
      w *= 0.5;
    }
    if (raw <= 110) {
      const v = raw / 10;
      if (v > cs) {
        b = Math.max(b - (v - cs), 0);
        w += v - cs;
      } else {
        b = D_PRIME - (D_PRIME - b) * Math.exp(-1 / (tau(v) * (wear ? 2 - Math.exp(-w / 400) : 1)));
      }
    }
    return (100 * b) / D_PRIME;
  });
}

const fillText = (t: string, v: Record<string, string | number>) =>
  t.replace(/\{(\w+)\}/g, (_, k) => String(v[k] ?? ""));

/** The published model and ours, over his whole match, with a crosshair readout. */
function CompareChart({ data, item, name, text }: Props & { item: Item }) {
  const [hover, setHover] = useState<number | null>(null);
  const s = data.signals[item.player!];
  const series = VARIANTS.map((v) => typicalBattery(s, v));
  const n = s.speed.length;
  const H = 170;
  const end = data.duration;
  const x = (k: number) => PAD.l + (signalTime(s, k) / end) * (WIDTH - PAD.l - PAD.r);
  const y = (v: number) => PAD.t + (1 - (Math.max(v, 40) - 40) / 60) * (H - PAD.t - PAD.b);
  const path = (vs: number[]) => {
    let d = "";
    for (let k = 0; k < n; k += 5) d += `${k ? "L" : "M"}${x(k).toFixed(1)},${y(vs[k]).toFixed(1)}`;
    return d;
  };
  const onMove = (e: React.MouseEvent<SVGSVGElement>) => {
    const r = e.currentTarget.getBoundingClientRect();
    const v = (((e.clientX - r.left) / r.width) * WIDTH - PAD.l) / (WIDTH - PAD.l - PAD.r) * end;
    const k = signalIndex(s, v);
    setHover(k);
  };
  const cls = ["std", "slow", `ours ${item.team}`];
  const half = data.meta.periods[1]?.video_start;
  return (
    <figure className="chart how-chart compare-chart">
      <figcaption>
        <strong>{fillText(text.howCompareTitle, { name })}</strong>
        <span className="sub">{text.howCompareSub}</span>
      </figcaption>
      <ul className="legend">
        {[text.howCompareStd, text.howCompareSlow, text.howCompareOurs].map((l, j) => (
          <li key={l}><svg width="26" height="8" aria-hidden="true"><line x1="0" x2="26" y1="4" y2="4" className={`line ${cls[j]}`} /></svg>{l}</li>
        ))}
      </ul>
      <svg viewBox={`0 0 ${WIDTH} ${H}`} role="img" aria-label={fillText(text.howCompareTitle, { name })}
           onMouseMove={onMove} onMouseLeave={() => setHover(null)}>
        {[40, 70, 100].map((t) => (
          <g key={t}>
            <line x1={PAD.l} x2={WIDTH - PAD.r} y1={y(t)} y2={y(t)} className="grid" />
            <text x={PAD.l - 6} y={y(t) + 4} className="axis" textAnchor="end">{t}</text>
          </g>
        ))}
        <text x={4} y={12} className="axis axis-title">{text.howChartBattery}</text>
        {half !== undefined && (
          <line x1={PAD.l + (half / end) * (WIDTH - PAD.l - PAD.r)} x2={PAD.l + (half / end) * (WIDTH - PAD.l - PAD.r)}
                y1={PAD.t} y2={H - PAD.b} className="half" />
        )}
        {series.map((vs, j) => <path key={j} d={path(vs)} className={`line ${cls[j]}`} />)}
        {hover !== null && <line x1={x(hover)} x2={x(hover)} y1={PAD.t} y2={H - PAD.b} className="cross" />}
        {[0, n - 1].map((k) => (
          <text key={k} x={x(k)} y={H - 6} className="axis" textAnchor={k ? "end" : "start"}>
            {clockLabel(data.meta, signalTime(s, k))}</text>
        ))}
      </svg>
      <p className="readout" aria-live="polite">
        {hover === null ? text.howCompareHint : fillText(text.howCompareHover, {
          time: clockLabel(data.meta, signalTime(s, hover)),
          lo: Math.round(series[0][hover]), pct: Math.round(series[1][hover]), hi: Math.round(series[2][hover]) })}
      </p>
    </figure>
  );
}

const WINDOWS: [number, string][] = [[1, "1 s"], [3, ""], [10, "10 s"], [30, ""], [60, "1 min"],
  [180, ""], [300, "5 min"], [600, "10 min"], [1200, "20 min"]];

/** His best average speed (km/h) over each window, within one half. */
function bestAverages(s: Signals): (number | null)[] {
  const hs = s.halves?.map((h) => h[1]) ?? [0];
  const cuts = [...hs, s.speed.length];
  return WINDOWS.map(([w]) => {
    let best: number | null = null;
    for (let h = 0; h + 1 < cuts.length; h++) {
      let sum = 0;
      let bad = 0;
      for (let i = cuts[h]; i < cuts[h + 1]; i++) {
        const add = s.speed[i];
        sum += add <= 110 ? add : 0;
        bad += add <= 110 ? 0 : 1;
        if (i - cuts[h] >= w) {
          const out = s.speed[i - w];
          sum -= out <= 110 ? out : 0;
          bad -= out <= 110 ? 0 : 1;
        }
        if (i - cuts[h] >= w - 1 && bad === 0) best = Math.max(best ?? 0, (sum / w / 10) * 3.6);
      }
    }
    return best;
  });
}

/** His fastest average speed for each length of time, against a typical pro's critical speed. */
function ProfileChart({ data, item, name, text }: Props & { item: Item }) {
  const vals = bestAverages(data.signals[item.player!]);
  const H = 170;
  const lx = (w: number) => Math.log10(w);
  const x = (w: number) => PAD.l + 8 + ((lx(w) - lx(1)) / (lx(1200) - lx(1))) * (WIDTH - PAD.l - PAD.r - 40);
  const y = (v: number) => PAD.t + (1 - v / 36) * (H - PAD.t - PAD.b);
  const pts = WINDOWS.map(([w], j) => [w, vals[j]] as const).filter((p): p is readonly [number, number] => p[1] !== null);
  const label = new Set([1, 60, 600]);
  return (
    <figure className="chart how-chart">
      <figcaption>
        <strong>{fillText(text.howProfileTitle, { name })}</strong>
        <span className="sub">{text.howProfileSub}</span>
      </figcaption>
      <svg viewBox={`0 0 ${WIDTH} ${H}`} role="img" aria-label={fillText(text.howProfileTitle, { name })}>
        {[0, 15, 30].map((t) => (
          <g key={t}>
            <line x1={PAD.l} x2={WIDTH - PAD.r} y1={y(t)} y2={y(t)} className="grid" />
            <text x={PAD.l - 6} y={y(t) + 4} className="axis" textAnchor="end">{t}</text>
          </g>
        ))}
        <text x={4} y={12} className="axis axis-title">{text.howProfileAxis}</text>
        <line x1={PAD.l} x2={WIDTH - PAD.r} y1={y(CS_KMH)} y2={y(CS_KMH)} className="threshold" />
        <text x={WIDTH - PAD.r} y={y(CS_KMH) - 5} className="direct" textAnchor="end">{text.howProfileCs}</text>
        <path d={pts.map(([w, v], j) => `${j ? "L" : "M"}${x(w).toFixed(1)},${y(v).toFixed(1)}`).join("")}
              className={`line ${item.team}`} />
        {pts.map(([w, v]) => (
          <g key={w}>
            <circle cx={x(w)} cy={y(v)} r={4} className={`marker ${item.team}`}>
              <title>{`${WINDOWS.find((p) => p[0] === w)![1] || `${w} s`}: ${v.toFixed(1)} km/h`}</title>
            </circle>
            {label.has(w) && <text x={x(w) + 7} y={y(v) - 7} className="direct">{v.toFixed(1)}</text>}
          </g>
        ))}
        {WINDOWS.filter(([, l]) => l).map(([w, l]) => (
          <text key={w} x={x(w)} y={H - 6} className="axis" textAnchor="middle">{l}</text>
        ))}
      </svg>
    </figure>
  );
}

/** Boxes joined by arrows; they wrap, and stack on a phone. */
function Flow({ steps, label }: { steps: string[]; label: string }) {
  return (
    <ol className="flow" aria-label={label}>
      {steps.map((s) => <li key={s}>{s}</li>)}
    </ol>
  );
}

export function HowItWorks({ data, item, name, text }: Props) {
  const list = (prefix: string) =>
    Object.keys(text).filter((k) => k.startsWith(prefix)).sort().map((k) => text[k]);
  return (
    <main className="how">
      <h2>{text.howTitle}</h2>

      <section className="how-part how-two">
        <div>
          <h3>{text.howBatteryTitle}</h3>
          {list("howBattery_").map((p) => <p key={p}>{cite(p)}</p>)}
          <p className="how-tech">{text.howBatteryTech}</p>
        </div>
        {item?.player && (
          <div>
            <BatteryChart data={data} item={item} name={name} text={text} />
            <ProfileChart data={data} item={item} name={name} text={text} />
            <CompareChart data={data} item={item} name={name} text={text} />
          </div>
        )}
      </section>

      <section className="how-part">
        <h3>{text.howAgentsTitle}</h3>
        <p>{text.howAgents_1}</p>
        <Flow steps={list("howAgentStep_")} label={text.howAgentsTitle} />
        <p>{text.howAgents_2}</p>
        <p>{cite(text.howAgentsCite)}</p>
        <p className="sub">{text.howAgents_3}</p>
        <p className="how-tech">{text.howAgentsTech}</p>
      </section>

      <section className="how-part how-two">
        <div>
          <h3>{text.howDataTitle}</h3>
          <ul className="how-list">{list("howData_").map((p) => <li key={p}>{p}</li>)}</ul>
          <p className="sub">{cite(text.howDataSynthetic)}</p>
        </div>
        <div>
          <h3>{text.howLiveTitle}</h3>
          <p className="sub">{text.howLiveIntro}</p>
          <ul className="how-list">{list("howLive_").map((p) => <li key={p}>{p}</li>)}</ul>
        </div>
      </section>

      <section className="how-part how-refs">
        <h3>{text.howRefTitle}</h3>
        {list("howRefGroup_").map((title, g) => {
          const refs = Object.keys(text).filter((k) => k.startsWith(`howRef_${g + 1}_`)).sort();
          return (
            <div key={title}>
              <h4>{title}</h4>
              <ol>
                {refs.map((k) => {
                  const [ref, url] = text[k].split(" https://");
                  return (
                    <li key={k} value={Number(k.split("_")[2])}>
                      {ref} <a href={`https://${url}`} target="_blank" rel="noreferrer">{`https://${url}`}</a>
                    </li>
                  );
                })}
              </ol>
            </div>
          );
        })}
      </section>

      <p className="how-more">
        {text.howMore} <a href={REPO} target="_blank" rel="noreferrer">{text.howMoreLink}</a>
      </p>
    </main>
  );
}
