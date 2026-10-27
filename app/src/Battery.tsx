import { type MatchData, type Mode, type Player, type TeamBlock, signalIndex } from "./data";

// The battery: what a player's running so far would leave a typical
// professional, never his own state. One shell drawn one way at every size: a
// continuous charge in the ink of its ground that never changes colour with its
// level, the percentage outside it, and in analyst mode the 10–90% band as brackets above and
// below. Goalkeepers get none, as on the pitch.
const POSITIONS = ["GK", "CB", "FB", "DM", "CM", "WM", "AM", "CF"];

const fill = (t: string, v: Record<string, string | number>) =>
  t.replace(/\{(\w+)\}/g, (_, k) => String(v[k] ?? ""));
const clamp = (v: number) => Math.min(Math.max(v, 0), 100);

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

/** The battery shell: a charge whose length is the percentage (none at 0%), and in analyst
 * mode the band's brackets, clear of the charge. */
export function Gauge({ r, mode, label, size = "big" }: {
  r: Reading;
  mode: Mode;
  label: string;
  size?: "big" | "small";
}) {
  const band = mode === "analyst" && r.lo !== null && r.hi !== null;
  const lo = band ? clamp(r.lo!) : 0;
  const hi = band ? clamp(r.hi!) : 0;
  return (
    <span className={`gauge ${size}${band ? " banded" : ""}`} role="meter" aria-valuemin={0}
          aria-valuemax={100} aria-valuenow={r.pct} aria-label={label} title={label}>
      <span className="gauge-shell">
        <span className="gauge-track">
          {r.pct > 0 && <span className="gauge-fill" style={{ width: `${clamp(r.pct)}%` }} />}
          {band && (
            <>
              <span className="gauge-band top" style={{ left: `${lo}%`, width: `${hi - lo}%` }} />
              <span className="gauge-band bottom" style={{ left: `${lo}%`, width: `${hi - lo}%` }} />
            </>
          )}
        </span>
      </span>
      <span className="gauge-nub" />
    </span>
  );
}

/** The brand: the same shell, empty, never a reading. */
export function BrandMark() {
  return (
    <svg className="brand-mark" viewBox="0 0 26 14" aria-hidden="true">
      <rect x={0.75} y={0.75} width={21.5} height={12.5} rx={2.5} />
      <rect x={23} y={4} width={2.5} height={6} rx={0.5} className="nub" />
    </svg>
  );
}

/** The broadcast lower third, docked under the pitch: the moment and its clock, whose it is,
 * and his battery as the clip plays. A team moment shows each team's running instead. */
export function LowerThird({ tag, clock, team, who, player, r, offPitch, mode, text, teamRun,
                             blockLabel, teams }: {
  tag: string;
  clock: string;
  team: string;
  who: string;
  player: Player | undefined;
  r: Reading | null;
  offPitch: boolean;
  mode: Mode;
  text: Record<string, string>;
  teamRun: TeamBlock | null;
  blockLabel: string;
  teams: { id: string; name: string }[];
}) {
  const label = r && player
    ? `${text.ltBatterySub}: ${r.pct}%${mode === "analyst" && r.lo !== null ? ` (${r.lo}–${r.hi}%)` : ""}`
    : "";
  return (
    <div className="lower-third">
      <div className="lt-who">
        <p className="lt-tag">{tag} · <span className="num">{clock}</span></p>
        <p className="lt-name">
          <span className={`chip ${team}`} aria-hidden="true" />
          {player && <span className="lt-shirt num">{player.shirt}</span>}
          <span className="lt-player">{player?.name ?? who}</span>
          {player && <span className="lt-pos">{player.position}</span>}
        </p>
      </div>
      {player ? (
        r ? (
          <div className="lt-battery">
            <div className="lt-gauge">
              <Gauge r={r} mode={mode} label={label} />
              <span className="lt-num">
                <strong className="lt-pct num">{r.pct}%</strong>
                {mode === "analyst" && r.lo !== null && (
                  <span className="lt-band num">({r.lo}–{r.hi}%)</span>
                )}
              </span>
            </div>
            <p className="lt-sub">{text.ltBatterySub}</p>
          </div>
        ) : offPitch ? (
          <p className="lt-sub lt-note">{fill(text.offPitch, { name: player.name })}</p>
        ) : null
      ) : (
        <div className="lt-teams">
          {teamRun ? (
            <>
              {teams.map((t) => {
                const v = teamRun[t.id as "home" | "away"]?.hsr;
                return (
                  <p key={t.id} className="lt-team">
                    <span className={`chip ${t.id}`} aria-hidden="true" />
                    <span className="lt-team-name">{t.name}</span>
                    <strong className="num">{v === null || v === undefined ? "–" : Math.round(v)}</strong>
                  </p>
                );
              })}
              <p className="lt-sub">{fill(text.ltTeamRunning, { block: blockLabel })}</p>
            </>
          ) : <p className="lt-sub lt-note">{text.hlNone}</p>}
        </div>
      )}
    </div>
  );
}

/** Both line-ups with each player's battery, live; a click follows that player. */
export function TeamSheet({ data, now, mode, on, text, onSelect }: {
  data: MatchData;
  now: number;
  mode: Mode;
  on: string | null;
  text: Record<string, string>;
  onSelect: (id: string) => void;
}) {
  const rank = (p: Player) => POSITIONS.indexOf(p.position) * 100 + p.shirt;
  return (
    <section className="sheet">
      <h3>{text.sheetTitle}</h3>
      <p className="sub">{text.sheetSub}</p>
      <div className="sheet-cols">
        {data.meta.teams.map((t) => (
          <div key={t.id} className="sheet-col">
            <h4><span className={`dot ${t.id}`} aria-hidden="true" />{t.name}</h4>
            <ol>
              {data.meta.players
                .filter((p) => p.team === t.id && signalIndex(data.signals[p.id], now) !== null)
                .sort((a, b) => rank(a) - rank(b))
                .map((p) => {
                  const r = reading(data, p, now);
                  return (
                    <li key={p.id}>
                      <button className={`sheet-row${p.id === on ? " on" : ""}`}
                              onClick={() => onSelect(p.id)}>
                        <span className="sheet-shirt num">{p.shirt}</span>
                        <span className="sheet-name">{p.name}</span>
                        {r ? (
                          <span className="sheet-battery">
                            <Gauge r={r} mode={mode} size="small"
                                   label={fill(text.battery, { name: p.name, pct: r.pct })} />
                            <span className="sheet-pct num">{r.pct}%</span>
                          </span>
                        ) : <span className="sheet-pos">{p.position}</span>}
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
