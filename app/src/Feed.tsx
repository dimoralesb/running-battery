import { type Feed as FeedData, type Mode } from "./data";

interface Props {
  feed: FeedData;
  now: number;
  mode: Mode;
  text: Record<string, string>;
  onSeek: (v: number, player: string | null) => void;
}

const fill = (t: string, v: Record<string, string | number>) =>
  t.replace(/\{(\w+)\}/g, (_, k) => String(v[k] ?? ""));

/** Full match: the agents' lines as they come, newest first (decision 49: no verdicts or blocked
 * lines on the page; the Verifier is in the README). */
export function Feed({ feed, now, mode, text, onSeek }: Props) {
  const mine = feed.entries.filter((e) => e.mode === mode && e.video_s <= now + 0.5);
  const shown = mine.filter((e) => e.shown).reverse();
  const later = feed.entries.filter((e) => e.mode === mode && e.shown && e.video_s > now).length;
  return (
    <div className="feed">
      <h3>{text.feedTitle}</h3>
      {shown.length === 0 && <p className="sub">{text.feedEmpty}</p>}
      {shown.map((e, k) => (
        <article key={`${e.moment_id}-${k}`}
                 className="line">
          <button className="line-meta" onClick={() => onSeek(e.video_s - 3, e.player?.id ?? null)}>
            <span className="num">{e.clock}</span>
            <span className={`dot ${e.team}`} aria-hidden="true" />
            <span>{e.player ? e.player.name : fill(text.teamLine, { team: e.team_name })}</span>
          </button>
          <p>{e.sentence}</p>
        </article>
      ))}
      {later > 0 && <p className="sub">{fill(text.feedLater, { n: later })}</p>}
    </div>
  );
}
