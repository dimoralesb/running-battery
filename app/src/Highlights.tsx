import { type Highlight, type Meta, highlightValue, topSoFar } from "./data";

// The physical highlights so far (decision 28): per kind, the top 3 players, best first. A click
// plays that moment at 1×; "Play highlights" plays the whole match's best moments back to back.
export const KINDS: Highlight["kind"][] = ["top_speed", "longest_run", "back_to_back",
                                          "busiest_minute"];

interface Props {
  all: Highlight[];
  meta: Meta;
  now: number;
  active: Highlight | null;
  reelOn: boolean;
  text: Record<string, string>;
  onPick: (h: Highlight) => void;
  onReel: () => void;
}

export function Highlights({ all, now, active, reelOn, text, onPick, onReel }: Props) {
  if (!all.length) return null;
  return (
    <section className="card highlights">
      <div className="hl-head">
        <div>
          <h3>{text.hlTitle}</h3>
          <p className="muted small">{text.hlSub}</p>
        </div>
        <button className={reelOn ? "on" : ""} onClick={onReel}>
          {reelOn ? text.hlStop : text.hlPlay}
        </button>
      </div>
      <div className="hl-grid">
        {KINDS.map((kind) => {
          const top = topSoFar(all, kind, now);
          return (
            <div key={kind} className="hl-kind">
              <h4>{text[`hl_${kind}`]}</h4>
              {top.length === 0 && <p className="muted small">{text.hlNone}</p>}
              <ol>
                {top.map((h) => (
                  <li key={`${h.player.id}-${h.video_s}`}>
                    <button className={`hl-item${active === h ? " on" : ""}`}
                            onClick={() => onPick(h)} title={h.caption}>
                      <span className={`dot ${h.player.team}`} aria-hidden="true" />
                      <span className="hl-name">{h.player.name}</span>
                      <strong>{highlightValue(h)}</strong>
                      <span className="muted">{h.clock}</span>
                    </button>
                  </li>
                ))}
              </ol>
            </div>
          );
        })}
      </div>
    </section>
  );
}

/** The reel: the whole match's top 2 of each kind, in match order, overlapping moments merged. */
export function reel(all: Highlight[], end: number): Highlight[] {
  const picks = KINDS.flatMap((k) => topSoFar(all, k, end, 2));
  const out: Highlight[] = [];
  for (const h of [...picks].sort((a, b) => a.start_video_s - b.start_video_s)) {
    const last = out[out.length - 1];
    if (!last || h.start_video_s > last.end_video_s + 3) out.push(h);
  }
  return out;
}
