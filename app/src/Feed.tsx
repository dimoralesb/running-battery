import { type Entry, type Feed as FeedData, type Mode } from "./data";

interface Props {
  feed: FeedData;
  now: number;
  mode: Mode;
  favourite: string | null;
  showBlocked: boolean;
  text: Record<string, string>;
  onShowBlocked: (b: boolean) => void;
  onSeek: (v: number, player: string | null) => void;
}

const fill = (t: string, v: Record<string, string | number>) =>
  t.replace(/\{(\w+)\}/g, (_, k) => String(v[k] ?? ""));

/** Papers are cited by key (no dot, no space); the rest are the measured fields a line used. */
export const splitSources = (sources: string[]) => {
  const cites = sources.filter((s) => !s.includes(".") && !s.includes(" "));
  return [cites, sources.filter((s) => !cites.includes(s))];
};

/** Register claims that are our model's estimate, not a published finding (claims.json: the
 * typical-pro reserve, the steady-running equivalent, the fresh-legs area, "the lowest point of
 * his match by our estimate"; decision 39: 19c was labelled published research). */
const ESTIMATE_CLAIMS = new Set(["11", "12", "17", "19c"]);

/** A line's verdict and sources. Fans see one short label and open it for the claim, the papers
 * and the check; analysts get the full citation open (JOURNEY.md, verdict labels). */
export function Verdict({ e, mode, text }: { e: Entry; mode: Mode; text: Record<string, string> }) {
  const [cites, fields] = splitSources(e.sources);
  const blocked = e.verdict === "blocked";
  const cite = (e.claim === "fact" ? text.measuredFact : fill(text.claimLabel, { claim: e.claim }))
    + (cites.length ? ` · ${cites.join(", ")}` : "");
  const short = blocked ? text.verdictBlocked
    : e.claim === "fact" ? text.verdictMeasured
    : ESTIMATE_CLAIMS.has(e.claim) ? text.verdictEstimate : text.verdictResearch;
  const verdict = blocked ? text.verdictBlocked : text[`verdict_${e.verdict}`];
  const pipe = e.verdict === "fallback" || e.verdict === "template"
    ? text.checkedByTemplate : text.checkedBy;
  const mcp = e.kind === "tug_of_war" ? text.mcpTeam : text.mcpPlayer;
  return (
    <details className="verdict" open={mode === "analyst"}>
      <summary>{mode === "analyst" ? `${verdict} · ${cite}` : short}</summary>
      <ul>
        {mode === "fan" && <li>{cite}</li>}
        {fields.map((f) => <li key={f}><code>{f}</code></li>)}
        {e.verifier.stage && <li>{fill(pipe, { stage: e.verifier.stage })}</li>}
        <li>{mcp}</li>
        {e.original && <li>{text.beforeVerifier} <s>{e.original}</s></li>}
      </ul>
    </details>
  );
}

/** A blocked line, struck through, with the rule it broke. */
export function Blocked({ e, text }: { e: Entry; text: Record<string, string> }) {
  return (
    <>
      <p><s>{e.sentence}</s></p>
      {e.verifier.findings.map((f, j) => (
        <p key={j} className="reason">
          {f.stage === "llm" ? text.llmStage : text.ruleStage} · {f.claim}: {f.message}
        </p>
      ))}
    </>
  );
}

/** Full match: the agents' lines as they come, newest first. */
export function Feed({ feed, now, mode, favourite, showBlocked, text, onShowBlocked, onSeek }: Props) {
  const mine = feed.entries.filter((e) => e.mode === mode && e.video_s <= now + 0.5);
  const shown = mine.filter((e) => e.shown).reverse();
  const blocked = mine.filter((e) => e.verdict === "blocked").reverse();
  const later = feed.entries.filter((e) => e.mode === mode && e.shown && e.video_s > now).length;
  return (
    <div className="feed">
      <div className="feed-head">
        <h3>{text.feedTitle}</h3>
        <label className="check">
          <input type="checkbox" checked={showBlocked}
                 onChange={(e) => onShowBlocked(e.target.checked)} /> {text.showBlocked}
        </label>
      </div>
      {showBlocked && (
        <div className="blocked-list">
          <p className="sub">{text.blocked}</p>
          {blocked.length === 0 && <p className="sub">{text.nothingBlocked}</p>}
          {blocked.map((e, k) => (
            <article key={k} className="line blocked">
              <p className="line-meta num">{e.clock} · {e.player?.name ?? e.team_name}</p>
              <Blocked e={e} text={text} />
            </article>
          ))}
        </div>
      )}
      {shown.length === 0 && <p className="sub">{text.feedEmpty}</p>}
      {shown.map((e, k) => (
        <article key={`${e.moment_id}-${k}`}
                 className={`line${e.player && e.player.id === favourite ? " fav" : ""}`}>
          <button className="line-meta" onClick={() => onSeek(e.video_s - 3, e.player?.id ?? null)}>
            <span className="num">{e.clock}</span>
            <span className={`dot ${e.team}`} aria-hidden="true" />
            <span>{e.player ? e.player.name : fill(text.teamLine, { team: e.team_name })}</span>
          </button>
          <p>{e.sentence}</p>
          <Verdict e={e} mode={mode} text={text} />
        </article>
      ))}
      {later > 0 && <p className="sub">{fill(text.feedLater, { n: later })}</p>}
    </div>
  );
}
