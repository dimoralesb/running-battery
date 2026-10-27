import { type Item, type MatchData, clockLabel, signalIndex } from "./data";

// "How it works" (decision 52): the third view, for judges and the curious. Plain sentences first,
// then the numbers, all from the README and checked by the Verifier's copy test (copy.json "how*").
// The battery chart uses the opening clip's player, around his run, from this match's own data.

const REPO = "https://github.com/dimoralesb/running-battery#readme";
const CS = 4.1; // m/s, the typical pro's critical speed (engine prior, PLAN decision 13)
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

/** His speed and the typical-pro battery, second by second, from 90 s before the clip's run to
 * 8 minutes after it, within its half: the drain in the run and the refill after it (the story
 * match's 3:50 run takes the battery from 90% to 60%, back to 86% by 11:30). */
function BatteryChart({ data, item, name, text }: Props & { item: Item }) {
  const s = data.signals[item.player!];
  const half = data.meta.periods.filter((p) => p.video_start <= item.start).at(-1) ?? data.meta.periods[0];
  const a = Math.floor(Math.max(item.start - 90, half.video_start));
  const b = Math.ceil(Math.min(item.end + 480, half.video_start + half.duration_s - 1));
  const speed: (number | null)[] = [];
  const battery: (number | null)[] = [];
  for (let v = a; v <= b; v++) {
    const i = signalIndex(s, v);
    speed.push(i !== null && s.speed[i] <= 110 ? s.speed[i] / 10 : null);
    battery.push(i !== null ? s.battery[i] : null);
  }
  const n = speed.length;
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
        {item.segments.map(([s0, s1]) => (
          <rect key={s0} x={x(Math.max(s0 - a, 0))} y={PAD.t}
                width={Math.max(x(Math.min(s1 - a, n - 1)) - x(Math.max(s0 - a, 0)), 1)}
                height={h - PAD.t - PAD.b} className="zone run" />
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
      {panel(150, 10, [0, 5, 10], text.howChartSpeed, speed, CS)}
      {panel(130, 100, [0, 50, 100], text.howChartBattery, battery)}
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
      <p className="how-intro">{text.howIntro}</p>

      <section className="how-part how-two">
        <div>
          <h3>{text.howBatteryTitle}</h3>
          {list("howBattery_").map((p) => <p key={p}>{p}</p>)}
        </div>
        {item?.player && <BatteryChart data={data} item={item} name={name} text={text} />}
      </section>

      <section className="how-part">
        <h3>{text.howAgentsTitle}</h3>
        <p>{text.howAgents_1}</p>
        <Flow steps={list("howAgentStep_")} label={text.howAgentsTitle} />
        <div className="how-two">
          <div>
            <p>{text.howAgents_2}</p>
            <p className="sub">{text.howAgents_3}</p>
          </div>
          <div className="table-wrap">
            <table className="how-table">
              <thead>
                <tr><th />{[text.howVerCaught, text.howVerBlocked].map((h) => <th key={h}>{h}</th>)}</tr>
              </thead>
              <tbody>
                <tr><th scope="row">{text.howVerRules}</th><td className="num">87 / 119</td><td className="num">0 / 73</td></tr>
                <tr><th scope="row">{text.howVerBoth}</th><td className="num">116 / 119</td><td className="num">1 / 73</td></tr>
              </tbody>
            </table>
          </div>
        </div>
      </section>

      <section className="how-part how-two">
        <div>
          <h3>{text.howDataTitle}</h3>
          <ul className="how-list">{list("howData_").map((p) => <li key={p}>{p}</li>)}</ul>
          <p className="sub">{text.howDataSynthetic}</p>
        </div>
        <div>
          <h3>{text.howLiveTitle}</h3>
          <p className="sub">{text.howLiveIntro}</p>
          <ol className="how-steps">{list("howLive_").map((p) => <li key={p}>{p}</li>)}</ol>
        </div>
      </section>

      <p className="how-more">
        {text.howMore} <a href={REPO} target="_blank" rel="noreferrer">{text.howMoreLink}</a>
      </p>
    </main>
  );
}
