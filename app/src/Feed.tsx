import { type Entry, type Feed as FeedData, type Meta, type Mode } from "./data";

interface Props {
  feed: FeedData;
  meta: Meta;
  now: number;
  mode: Mode;
  favourite: string | null;
  showBlocked: boolean;
  blockedNote: string;
  onShowBlocked: (b: boolean) => void;
  onSeek: (v: number, player: string | null) => void;
}

export const VERDICT: Record<Entry["verdict"], string> = {
  pass: "Verified",
  rewritten: "Rewritten by the Verifier",
  fallback: "Template (the agent's line was blocked)",
  template: "Template (plain code)",
  repeat: "Held back (said twice already)",
  blocked: "Blocked",
};

export function Sources({ e }: { e: Entry }) {
  const cites = e.sources.filter((s) => !s.includes(".") && !s.includes(" "));
  const fields = e.sources.filter((s) => !cites.includes(s));
  return (
    <details className="sources">
      <summary>
        {e.claim === "fact" ? "Measured fact" : `Claim ${e.claim}`}
        {cites.length ? ` · ${cites.join(", ")}` : ""}
      </summary>
      <ul>
        {fields.map((f) => <li key={f}><code>{f}</code></li>)}
        {e.verifier.stage && <li>Checked by: {e.verifier.stage}</li>}
        {e.original && <li>Before the Verifier: <s>{e.original}</s></li>}
      </ul>
    </details>
  );
}

export function Feed({ feed, now, mode, favourite, showBlocked, blockedNote, onShowBlocked,
                       onSeek }: Props) {
  const mine = feed.entries.filter((e) => e.mode === mode && e.video_s <= now + 0.5);
  const shown = mine.filter((e) => e.shown).reverse();
  const blocked = mine.filter((e) => e.verdict === "blocked").reverse();
  const later = feed.entries.filter((e) => e.mode === mode && e.shown && e.video_s > now).length;
  return (
    <div className="feed">
      <div className="feed-head">
        <h2>Live explanations</h2>
        <label className="small">
          <input type="checkbox" checked={showBlocked}
                 onChange={(e) => onShowBlocked(e.target.checked)} /> What the Verifier blocked
        </label>
      </div>
      {showBlocked && (
        <div className="blocked-list">
          <p className="muted small">{blockedNote}</p>
          {blocked.length === 0 && <p className="muted small">Nothing blocked so far.</p>}
          {blocked.map((e, k) => (
            <div key={k} className="entry blocked">
              <div className="meta"><span>{e.clock}</span> <span>{e.player?.name ?? e.team_name}</span></div>
              <p><s>{e.sentence}</s></p>
              {e.verifier.findings.map((f, j) => (
                <p key={j} className="small reason">
                  {f.stage === "llm" ? "LLM check" : "Rule"} · {f.claim}: {f.message}
                </p>
              ))}
            </div>
          ))}
        </div>
      )}
      {shown.length === 0 && (
        <p className="muted">The first explanation comes with the first moment. Press play or
          pick a moment.</p>
      )}
      {shown.map((e, k) => (
        <article key={`${e.moment_id}-${k}`}
                 className={`entry ${e.team}${e.player && e.player.id === favourite ? " fav" : ""}`}>
          <button className="meta" onClick={() => onSeek(e.video_s - 3, e.player?.id ?? null)}>
            <span>{e.clock}</span>
            <span className={`dot ${e.team}`} aria-hidden="true" />
            <span>{e.player ? e.player.name : `${e.team_name} (team)`}</span>
          </button>
          <p>{e.sentence}</p>
          <div className="foot">
            <span className={`badge ${e.verdict}`}>{VERDICT[e.verdict]}</span>
            <Sources e={e} />
          </div>
        </article>
      ))}
      {later > 0 && <p className="muted small">{later} more later in the match.</p>}
    </div>
  );
}
