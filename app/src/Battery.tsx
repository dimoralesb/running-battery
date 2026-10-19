import { type MatchData, type Mode, type Player, signalIndex } from "./data";

// The battery (decision 14, decision 32): what a player's running so far would leave a typical
// professional, never his own state. A continuous fill (decision 33: five levels hid every change
// within a level), with the percentage; analyst mode adds the 10–90% band. Goalkeepers get none, as on the pitch.
const POSITIONS = ["GK", "CB", "FB", "DM", "CM", "WM", "AM", "CF"];

const fill = (t: string, v: Record<string, string | number>) =>
  t.replace(/\{(\w+)\}/g, (_, k) => String(v[k] ?? ""));

export interface Reading {
  pct: number;
  lo: number | null;
  hi: number | null;
}

/** The battery reading of one player at `now`, or null off the pitch (or a goalkeeper). */
export function reading(data: MatchData, p: Player | undefined, now: number): Reading | null {
  if (!p || p.position === "GK") return null;
  const s = data.signals[p.id];
  const i = signalIndex(s, now);
  if (!s || i === null) return null;
  return { pct: s.battery[i], lo: s.lo ? s.lo[i] : null, hi: s.hi ? s.hi[i] : null };
}

/** A battery-shaped gauge: a continuous fill, and in analyst mode its 10–90% band. */
export function Gauge({ r, mode, label, size = "big" }: {
  r: Reading;
  mode: Mode;
  label: string;
  size?: "big" | "small";
}) {
  const at = (v: number) => `calc(2px + (100% - 4px) * ${Math.min(Math.max(v, 0), 100) / 100})`;
  return (
    <span className={`gauge ${size}`} role="img" aria-label={label} title={label}>
      <span className="gauge-shell">
        <span className="gauge-fill" style={{ width: `calc(${at(r.pct)} - 2px)` }} />
        {mode === "analyst" && r.lo !== null && r.hi !== null && (
          <span className="gauge-band"
                style={{ left: at(r.lo), width: `calc(${at(r.hi)} - ${at(r.lo)})` }} />
        )}
      </span>
      <span className="gauge-nub" />
    </span>
  );
}

/** A broadcast lower third docked under the pitch: what the clip or moment is, whose it is, its
 * caption, and the player's battery as the clip plays. */
export function LowerThird({ tag, team, clock, who, player, caption, r, mode, text }: {
  tag: string;
  team: string;
  clock: string;
  who: string;
  player: Player | undefined;
  caption: string | null;
  r: Reading | null;
  mode: Mode;
  text: Record<string, string>;
}) {
  const label = r && player ? fill(text.battery, { name: player.name, pct: r.pct }) : "";
  return (
    <div className={`lower-third ${team}`}>
      <div className="lt-bar">
        <span className="lt-tag">{tag}</span>
        <span className="lt-who">
          {player && <span className="lt-shirt">{player.shirt}</span>}
          <span className="lt-name">{player?.name ?? who}</span>
          {player && <span className="lt-pos">{player.position}</span>}
        </span>
        <span className="lt-clock">{clock}</span>
        {r && (
          <span className="lt-battery">
            <span className="lt-battery-label">
              <strong>{text.ltBattery}</strong>
              <span>{text.ltBatterySub}</span>
            </span>
            <Gauge r={r} mode={mode} label={label} />
            <strong className="lt-pct">{r.pct}%</strong>
          </span>
        )}
      </div>
      {(caption || (mode === "analyst" && r && r.lo !== null)) && (
        <div className="lt-caption" aria-live="polite">
          {caption && <p>{caption}</p>}
          {mode === "analyst" && r && r.lo !== null && r.hi !== null && (
            <p className="lt-band">{fill(text.ltBand, { lo: r.lo, hi: r.hi })}</p>
          )}
        </div>
      )}
    </div>
  );
}

/** Both line-ups with each player's battery, live; a click follows that player. */
export function TeamSheet({ data, now, mode, on, favourite, text, onSelect }: {
  data: MatchData;
  now: number;
  mode: Mode;
  on: string | null;
  favourite: string | null;
  text: Record<string, string>;
  onSelect: (id: string) => void;
}) {
  const rank = (p: Player) => POSITIONS.indexOf(p.position) * 100 + p.shirt;
  return (
    <section className="sheet card">
      <header>
        <h3>{text.sheetTitle}</h3>
        <p className="muted small">{text.sheetSub}</p>
      </header>
      <div className="sheet-cols">
        {data.meta.teams.map((t) => (
          <div key={t.id} className={`sheet-col ${t.id}`}>
            <h4>{t.name}</h4>
            <ol>
              {data.meta.players
                .filter((p) => p.team === t.id && signalIndex(data.signals[p.id], now) !== null)
                .sort((a, b) => rank(a) - rank(b))
                .map((p) => {
                  const r = reading(data, p, now);
                  return (
                    <li key={p.id}>
                      <button className={`sheet-row${p.id === on ? " on" : ""}${p.id === favourite ? " fav" : ""}`}
                              onClick={() => onSelect(p.id)}>
                        <span className="sheet-shirt">{p.shirt}</span>
                        <span className="sheet-name">{p.name}</span>
                        {r ? (
                          <span className="sheet-battery">
                            <Gauge r={r} mode={mode} size="small"
                                   label={fill(text.battery, { name: p.name, pct: r.pct })} />
                            <span className="sheet-pct">{r.pct}%</span>
                          </span>
                        ) : <span className="sheet-pos muted">{p.position}</span>}
                      </button>
                    </li>
                  );
                })}
            </ol>
          </div>
        ))}
      </div>
    </section>
  );
}
