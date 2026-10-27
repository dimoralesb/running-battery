import { type Entry, type MatchData, type Mode, type TeamBlock, clockLabel } from "./data";
import { SplitChart } from "./SplitChart";
import { TeamChart } from "./TeamChart";

// The Stats tab (decision 46): the teams' running over the whole match, as statistics, not clips.
// A team moment ("Westerlyn Albion did 19% more high-speed running per ball-in-play minute in
// 15:00–30:00") compares fifteen minutes; its clip showed a few seconds of them, at times a dead
// ball. Here each 15-minute block has both teams' numbers, its team lines (decision 49: no
// verdicts or blocked lines on the page), and a link to the full match there; then the two team
// charts.

interface Props {
  data: MatchData;
  mode: Mode;
  text: Record<string, string>;
  onWatch: (v: number) => void;
}

const fill = (t: string, v: Record<string, string | number>) =>
  t.replace(/\{(\w+)\}/g, (_, k) => String(v[k] ?? ""));

/** Each half's 15-minute blocks (the last runs to the half's end), both teams' high-speed
 * running per ball-in-play minute in it: the 5-minute blocks weighted by ball-in-play time, as the
 * lower third and the team lines count them (App.tsx teamBlock). */
export function blocks15(d: MatchData): TeamBlock[] {
  const out: TeamBlock[] = [];
  for (const p of d.meta.periods) {
    for (let k = 0; k < 3; k++) {
      const from = p.video_start + 900 * k;
      const to = k === 2 ? p.video_start + p.duration_s : from + 900;
      const parts = d.meta.team_running.filter((b) => b.video_start >= from - 0.01
                                                      && b.video_end <= to + 0.01);
      if (!parts.length) continue;
      const side = (key: "home" | "away") => {
        const s = parts.reduce((a, b) => a + b[key].in_play_s, 0);
        const known = parts.every((b) => b[key].hsr !== null);
        const hsr = known && s > 0
          ? parts.reduce((a, b) => a + (b[key].hsr ?? 0) * b[key].in_play_s, 0) / s : null;
        return { hsr, possession: parts[0][key].possession, in_play_s: s };
      };
      out.push({ video_start: parts[0].video_start, video_end: parts.at(-1)!.video_end,
                 clock: parts[0].clock, home: side("home"), away: side("away") });
    }
  }
  return out;
}

export function Stats({ data, mode, text, onWatch }: Props) {
  const { meta } = data;
  const blocks = blocks15(data);
  const lines = data.feed.entries.filter((e) => e.kind === "tug_of_war" && e.mode === mode);
  // A team line's key second is its block's last (the block it compares).
  const inBlock = (e: Entry, b: TeamBlock) => e.video_s > b.video_start && e.video_s <= b.video_end + 1;
  const label = (b: TeamBlock) => `${clockLabel(meta, b.video_start)}–${clockLabel(meta, b.video_end)}`;
  const rate = (v: number | null) => (v === null ? "–" : `${Math.round(v)}`);
  return (
    <div className="match-stats">
      <h3>{text.statsTitle}</h3>
      <p className="sub">{text.statsSub}</p>
      <ol className="stat-blocks">
        {blocks.map((b) => {
          const mine = lines.filter((e) => inBlock(e, b));
          return (
            <li key={b.video_start} className="stat-block">
              <div className="stat-head">
                <span className="num stat-when">{label(b)}</span>
                <button className="link" onClick={() => onWatch(b.video_start)}>
                  {fill(text.statsWatch, { block: label(b) })}
                </button>
              </div>
              <div className="stat-teams">
                {meta.teams.map((t) => (
                  <span key={t.id} className="stat-team">
                    <span className={`dot ${t.id}`} aria-hidden="true" />
                    <span>{t.name}</span>
                    <strong className="num">{rate(b[t.id as "home" | "away"].hsr)}</strong>
                    <span className="muted">{text.statsUnit}</span>
                  </span>
                ))}
              </div>
              {mine.filter((e) => e.shown).map((e, k) => (
                <article key={`s${k}`} className="line"><p>{e.sentence}</p></article>
              ))}
            </li>
          );
        })}
      </ol>
      <TeamChart meta={meta} now={data.duration} title={text.teamChart} sub={text.teamChartSub}
                 yTitle={text.teamChartAxis} onSeek={onWatch} />
      <SplitChart meta={meta} text={text} scope={text.splitWhole} blocks={meta.team_situations} />
    </div>
  );
}
