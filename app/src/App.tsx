import { useEffect, useMemo, useRef, useState } from "react";
import copy from "./copy.json";
import {
  MATCHES,
  type MatchData,
  type Mode,
  clockLabel,
  loadMatch,
  score,
  signalIndex,
} from "./data";
import { Feed } from "./Feed";
import { Legend, Pitch } from "./Pitch";
import { Trace } from "./Trace";

const SPEEDS = [1, 5, 20];
// Start state from the URL (for links and video capture): ?match=story&t=3500&mode=analyst&player=H04
const QUERY = new URLSearchParams(window.location.search);

export function fill(text: string, values: Record<string, string | number>): string {
  return text.replace(/\{(\w+)\}/g, (_, k) => String(values[k] ?? ""));
}

export default function App() {
  const [matchId, setMatchId] = useState(QUERY.get("match") ?? MATCHES[0].id);
  const [data, setData] = useState<MatchData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [now, setNow] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(5);
  const [mode, setMode] = useState<Mode>(QUERY.get("mode") === "analyst" ? "analyst" : "fan");
  const [selected, setSelected] = useState<string | null>(null);
  const [favourite, setFavourite] = useState<string | null>(null);
  const [showBlocked, setShowBlocked] = useState(false);

  useEffect(() => {
    setData(null);
    setError(null);
    loadMatch(matchId)
      .then((d) => {
        setData(d);
        const t = Number(QUERY.get("t"));
        setNow(Number.isFinite(t) && t > 0 ? t : d.feed.moments[0]?.video_s ?? 0);
        setSelected(QUERY.get("player") ?? d.feed.entries[0]?.player.id ?? null);
      })
      .catch((e) => setError(String(e)));
  }, [matchId]);

  // Play: advance replay time with the wall clock.
  const last = useRef<number | null>(null);
  useEffect(() => {
    if (!playing || !data) return;
    let raf = 0;
    const tick = (ms: number) => {
      if (last.current !== null) {
        const dt = ((ms - last.current) / 1000) * speed;
        setNow((v) => Math.min(v + dt, data.duration - 1));
      }
      last.current = ms;
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => {
      cancelAnimationFrame(raf);
      last.current = null;
    };
  }, [playing, speed, data]);

  const players = useMemo(
    () => (data ? Object.fromEntries(data.meta.players.map((p) => [p.id, p])) : {}),
    [data],
  );

  if (error) return <div className="app"><p className="muted">Could not load the match: {error}</p></div>;
  if (!data) return <div className="app"><p className="muted">Loading the match…</p></div>;

  const sc = score(data.meta, now);
  const [home, away] = data.meta.teams;
  const sel = selected ? players[selected] : null;
  const s = selected ? data.signals[selected] : undefined;
  const i = signalIndex(s, now);

  return (
    <div className="app">
      <header className="top">
        <div className="brand">
          <strong>Second Wind</strong>
          <span className="muted">who has done the most hard running, and when it costs them</span>
        </div>
        <div className="controls">
          <select value={matchId} onChange={(e) => setMatchId(e.target.value)} aria-label="Match">
            {MATCHES.map((m) => (
              <option key={m.id} value={m.id}>{m.label}</option>
            ))}
          </select>
          <div className="toggle" role="group" aria-label="Mode">
            {(["fan", "analyst"] as Mode[]).map((m) => (
              <button key={m} className={mode === m ? "on" : ""} onClick={() => setMode(m)}>
                {m === "fan" ? "Fan" : "Analyst"}
              </button>
            ))}
          </div>
          <select
            value={favourite ?? ""}
            onChange={(e) => setFavourite(e.target.value || null)}
            aria-label="Favourite player"
          >
            <option value="">Favourite player…</option>
            {data.meta.teams.map((t) => (
              <optgroup key={t.id} label={t.name}>
                {data.meta.players.filter((p) => p.team === t.id).map((p) => (
                  <option key={p.id} value={p.id}>{p.shirt} {p.name}</option>
                ))}
              </optgroup>
            ))}
          </select>
        </div>
      </header>

      <div className="scoreline">
        <span className="team home">{home.name}</span>
        <span className="score">{sc.home}–{sc.away}</span>
        <span className="team away">{away.name}</span>
        <span className="clock">{clockLabel(data.meta, now)}</span>
      </div>

      <main className="grid">
        <section className="left">
          <Pitch data={data} now={now} mode={mode} selected={selected} favourite={favourite}
                 onSelect={setSelected} />
          <Legend mode={mode} batteryText={copy.legendBattery} />
          <div className="transport">
            <button onClick={() => setPlaying((p) => !p)} aria-label={playing ? "Pause" : "Play"}>
              {playing ? "Pause" : "Play"}
            </button>
            <input type="range" min={0} max={data.duration - 1} step={1} value={now}
                   onChange={(e) => setNow(Number(e.target.value))} aria-label="Match time" />
            <div className="toggle" role="group" aria-label="Speed">
              {SPEEDS.map((x) => (
                <button key={x} className={speed === x ? "on" : ""} onClick={() => setSpeed(x)}>
                  {x}×
                </button>
              ))}
            </div>
          </div>
          <div className="moments">
            {data.feed.moments.map((m) => (
              <button key={m.moment_id} className="chip" onClick={() => setNow(m.video_s - 3)}>
                {m.clock} {KIND[m.kind] ?? m.kind}
              </button>
            ))}
          </div>
          <div className="card player-card">
            {sel ? (
              i === null || !s ? (
                <p>{fill(copy.offPitch, { name: sel.name })}</p>
              ) : (
                <>
                  <h3>{sel.shirt} {sel.name} <span className="muted">{sel.position}, {sel.team_name}</span></h3>
                  <p>{fill(copy.battery, { name: sel.name, pct: s.battery[i] })}</p>
                  {mode === "analyst" && s.lo && s.hi && (
                    <p className="muted">{fill(copy.band, { lo: s.lo[i], hi: s.hi[i] })}</p>
                  )}
                  {mode === "analyst" && s.low_chance && (
                    <p className="muted">{fill(copy.lowChance, {
                      chance: s.low_chance[i] < 1 ? "less than 1%" : `about ${s.low_chance[i]}%`,
                    })}</p>
                  )}
                  {s.red_zone[i] ? <p>{fill(copy.redZone, { name: sel.name })}</p>
                    : s.post_peak[i] ? <p>{fill(copy.postPeak, { name: sel.name })}</p> : null}
                </>
              )
            ) : (
              <p className="muted">Click a player on the pitch.</p>
            )}
          </div>
          {mode === "analyst" && sel && s && (
            <Trace signals={s} meta={data.meta} now={now} name={sel.name} onSeek={setNow} />
          )}
          <p className="muted small">{copy.disclaimer}</p>
        </section>
        <aside className="right">
          <Feed feed={data.feed} meta={data.meta} now={now} mode={mode} favourite={favourite}
                showBlocked={showBlocked} onShowBlocked={setShowBlocked} onSeek={(v, p) => {
                  setNow(v);
                  setSelected(p);
                }} blockedNote={copy.blocked} />
        </aside>
      </main>
    </div>
  );
}

export const KIND: Record<string, string> = {
  red_zone: "Red zone",
  exposed_on_turnover: "Exposed on the turnover",
  second_wind: "Second wind",
  fresh_legs: "Fresh legs",
  not_tired_tactical: "Not tired, tactical",
};
