import { type Highlight, type Meta, highlightValue, topSoFar } from "./data";

// The physical highlights so far: per kind, the top 3 players, best first. A
// click opens that moment in the Highlights view. One card per kind, surnames, a clip
// removed by hand is a plain row, and "Play highlights" is step 1's only.
export const KINDS: Highlight["kind"][] = ["top_speed", "longest_run", "recovery_run",
                                          "back_to_back", "busiest_minute", "most_ground"];

interface Props {
  all: Highlight[];
  meta: Meta;
  now: number;
  text: Record<string, string>;
  hidden: (h: Highlight) => boolean; // its clip was removed by hand: no link
  onPick: (h: Highlight) => void;
}

export function Highlights({ all, now, text, hidden, onPick }: Props) {
  if (!all.length) return null;
  return (
    <section className="highlights">
      <h3>{text.hlTitle}</h3>
      <p className="sub">{text.hlSub}</p>
      <div className="hl-grid">
        {KINDS.map((kind) => {
          const top = topSoFar(all, kind, now);
          return (
            <div key={kind} className="hl-kind">
              <h4>{text[`hl_${kind}`]}</h4>
              {top.length === 0 && (
                <p className="muted small">{kind === "most_ground" ? text.hlAtEnd : text.hlNone}</p>
              )}
              <ol>
                {top.map((h) => {
                  const row = (
                    <>
                      <span className={`dot ${h.player.team}`} aria-hidden="true" />
                      <span className="hl-name">{h.player.name.split(" ").slice(-1)[0]}</span>
                      <strong className="num">{highlightValue(h)}</strong>
                      <span className="muted num">{h.clock}</span>
                    </>
                  );
                  return (
                    <li key={`${h.player.id}-${h.video_s}`}>
                      {hidden(h) ? <span className="hl-item off" title={h.caption}>{row}</span> : (
                        <button className="hl-item" onClick={() => onPick(h)} title={h.caption}>{row}</button>
                      )}
                    </li>
                  );
                })}
              </ol>
            </div>
          );
        })}
      </div>
    </section>
  );
}

// When clips overlap (one run can be the longest, the fastest and the busiest minute), the one
// whose kind comes first here is kept.
const PRIORITY: Highlight["kind"][] = ["longest_run", "recovery_run", "top_speed", "back_to_back",
                                      "busiest_minute"];

/** The reel: the whole match's top 2 of each kind, in match order, overlapping clips merged
 * (by PRIORITY); the most ground covered (the whole match) comes last. */
export function reel(all: Highlight[], end: number): Highlight[] {
  const picks = PRIORITY.flatMap((k) => topSoFar(all, k, end, 2));
  const out: Highlight[] = [];
  for (const h of picks) {
    if (!out.some((o) => h.start_video_s <= o.end_video_s + 3 && o.start_video_s <= h.end_video_s + 3)) {
      out.push(h);
    }
  }
  return [...out.sort((a, b) => a.start_video_s - b.start_video_s),
          ...topSoFar(all, "most_ground", end, 1)];
}
