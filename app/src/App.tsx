import { useEffect, useMemo, useRef, useState } from "react";
import copy from "./copy.json";
import {
  type Item,
  MATCHES,
  type MatchData,
  type Mode,
  clockLabel,
  itemOfHighlight,
  loadMatch,
  queue,
  score,
  signalIndex,
  topSoFar,
} from "./data";
import { Feed } from "./Feed";
import { Highlights, reel } from "./Highlights";
import { Legend, Pitch } from "./Pitch";
import { Replay } from "./Replay";
import { SplitChart } from "./SplitChart";
import { TeamChart } from "./TeamChart";
import { Trace } from "./Trace";

const SPEEDS = [1, 5, 20];
const REPLAY_SPEED = 0.5; // "Replay with details" plays the clip at half speed
const LAPSE_SPEED = 120; // most ground covered: the whole match in under a minute
const LAPSE_WATCH_MS = 4000; // its Watch step is a still of the whole path, held this long
const FOCUS_BEFORE = 8; // full match: a feed moment is in focus from 8 s before to 6 s after
const FOCUS_AFTER = 6;
// Start state from the URL (for links and video capture): ?view=full&match=story&t=3500&
// mode=analyst&player=H04; the Highlights view takes ?hl=<kind> (the match's best of a kind),
// ?moment=<kind or moment id> (with &player=), or ?item=<n>, then &step=watch|replay and &auto=1
// (play the clips one after another).
const QUERY = new URLSearchParams(window.location.search);
// ?theme=light|dark overrides the system setting (for screenshots).
const THEME = QUERY.get("theme");
if (THEME === "light" || THEME === "dark") document.documentElement.dataset.theme = THEME;

type View = "highlights" | "full";
type Step = "watch" | "replay";
const TEXT: Record<string, string> = copy;

export function fill(text: string, values: Record<string, string | number>): string {
  return text.replace(/\{(\w+)\}/g, (_, k) => String(values[k] ?? ""));
}

/** The URL's clip, if it names one. */
function itemFromUrl(d: MatchData, list: Item[]): Item | undefined {
  const hl = QUERY.get("hl") as Parameters<typeof topSoFar>[1] | null;
  if (hl) {
    const top = topSoFar(d.highlights, hl, d.duration, 1)[0];
    return top ? list.find((i) => i.h === top) ?? itemOfHighlight(top) : undefined;
  }
  const m = QUERY.get("moment");
  if (m) {
    const p = QUERY.get("player");
    return list.find((i) => i.source === "moment" && (i.id === m || i.kind === m)
                            && (!p || i.player === p));
  }
  const n = Number(QUERY.get("item"));
  return Number.isInteger(n) && n >= 1 ? list[n - 1] : undefined;
}

export default function App() {
  const [matchId, setMatchId] = useState(QUERY.get("match") ?? MATCHES[0].id);
  const [data, setData] = useState<MatchData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [view, setView] = useState<View>(QUERY.get("view") === "full" ? "full" : "highlights");
  const [now, setNow] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(5);
  const [mode, setMode] = useState<Mode>(QUERY.get("mode") === "analyst" ? "analyst" : "fan");
  const [selected, setSelected] = useState<string | null>(null);
  const [favourite, setFavourite] = useState<string | null>(null);
  const [showBlocked, setShowBlocked] = useState(false);
  const [allBatteries, setAllBatteries] = useState(QUERY.get("batteries") === "all");
  const [cur, setCur] = useState<Item | null>(null);
  const [step, setStep] = useState<Step>("watch");
  const [auto, setAuto] = useState(QUERY.get("auto") === "1");

  const items = useMemo(
    () => (data ? queue(data, mode, reel(data.highlights, data.duration)) : []),
    [data, mode],
  );

  // Play a clip from the start of a step.
  const start = (it: Item, st: Step) => {
    setCur(it);
    setStep(st);
    setView("highlights");
    if (it.player) setSelected(it.player);
    if (it.lapse && st === "watch") {
      setNow(it.end);
      setPlaying(false);
    } else {
      setNow(it.lapse ? 0 : Math.max(it.start - 3, 0));
      setSpeed(it.lapse ? LAPSE_SPEED : st === "watch" ? 1 : REPLAY_SPEED);
      setPlaying(true);
    }
  };

  useEffect(() => {
    setData(null);
    setError(null);
    loadMatch(matchId)
      .then((d) => {
        setData(d);
        const t = Number(QUERY.get("t"));
        const hasT = Number.isFinite(t) && t > 0;
        setNow(hasT ? t : d.feed.moments[0]?.video_s ?? 0);
        setSelected(QUERY.get("player") ?? d.feed.favourite
                    ?? d.feed.entries.find((e) => e.player)?.player?.id ?? null);
        setFavourite(QUERY.get("favourite") ?? d.feed.favourite ?? null);
        const list = queue(d, mode, reel(d.highlights, d.duration));
        const it = view === "highlights" ? itemFromUrl(d, list) ?? list[0] : undefined;
        if (it) {
          start(it, QUERY.get("step") === "replay" ? "replay" : "watch");
          if (hasT) setNow(t);
        }
      })
      .catch((e) => setError(String(e)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
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

  const ix = cur ? items.findIndex((i) => i.id === cur.id) : -1;
  const next = cur ? (ix >= 0 ? items[ix + 1] : items.find((i) => i.at > cur.at)) : items[0];
  const prev = cur && ix > 0 ? items[ix - 1] : undefined;

  // Watch, then Replay with details; after the replay, pause on the numbers (or, with "Play
  // highlights", go on to the next clip).
  useEffect(() => {
    if (view !== "highlights" || !cur || !playing || !data) return;
    const end = Math.min(cur.lapse ? cur.end : cur.end + 2, data.duration - 1);
    if (now < end) return;
    if (step === "watch") start(cur, "replay");
    else if (auto && next) start(next, "watch");
    else {
      setPlaying(false);
      if (auto) setAuto(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [now, playing]);
  // The whole-match path is a still in its Watch step.
  useEffect(() => {
    if (view !== "highlights" || !cur?.lapse || step !== "watch") return;
    const id = setTimeout(() => start(cur, "replay"), LAPSE_WATCH_MS);
    return () => clearTimeout(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cur, step, view]);

  const players = useMemo(
    () => (data ? Object.fromEntries(data.meta.players.map((p) => [p.id, p])) : {}),
    [data],
  );
  // Each player's fastest second so far, second by second (for the score bar).
  const topSoFarBy = useMemo(() => {
    if (!data) return {};
    return Object.fromEntries(Object.entries(data.signals).map(([id, s]) => {
      let top = 0;
      return [id, s.speed.map((v) => (top = v <= 110 && v > top ? v : top))];
    }));
  }, [data]);

  if (error) return <div className="app"><p className="muted">Could not load the match: {error}</p></div>;
  if (!data) return <div className="app"><p className="muted">Loading the match…</p></div>;

  const sc = score(data.meta, now);
  const [home, away] = data.meta.teams;
  const sel = selected ? players[selected] : null;
  const s = selected ? data.signals[selected] : undefined;
  const i = signalIndex(s, now);

  const fastest = (team: string) => {
    let best: { name: string; v: number } | null = null;
    for (const p of data.meta.players) {
      const sp = data.signals[p.id];
      const tops = topSoFarBy[p.id];
      if (p.team !== team || !sp || !tops || p.position === "GK") continue;
      const k = Math.min(Math.floor(now - sp.start), tops.length - 1);
      if (k < 0) continue;
      if (!best || tops[k] > best.v) best = { name: p.name, v: tops[k] };
    }
    return best && best.v > 0 ? (
      <span className="fastest muted small">{fill(copy.fastest, {
        name: best.name, v: (best.v / 10).toFixed(1), kmh: Math.round(best.v * 0.36),
      })}</span>
    ) : null;
  };

  // Full match: the feed moment on screen, its player and its first line.
  const moment = view === "full"
    ? data.feed.moments.find((m) => now >= m.video_s - FOCUS_BEFORE && now <= m.video_s + FOCUS_AFTER)
    : undefined;
  const momentLine = moment
    ? data.feed.entries.find((e) => e.moment_id === moment.moment_id && e.mode === mode && e.shown)
    : undefined;
  const focus = momentLine?.player?.id ?? null;

  const label = (it: Item) =>
    it.source === "highlight" ? TEXT[`hl_${it.kind}`] : KIND[it.kind] ?? it.kind;
  const who = (it: Item) =>
    it.player ? players[it.player]?.name : data.meta.teams.find((t) => t.id === it.team)?.name;

  return (
    <div className="app">
      <header className="top">
        <div className="brand">
          <strong>Second Wind</strong>
          <span className="muted">who has done the most hard running, and when it costs them</span>
        </div>
        <div className="controls">
          <div className="toggle" role="group" aria-label="View">
            <button className={view === "highlights" ? "on" : ""}
                    onClick={() => (cur ? start(cur, "watch") : items[0] && start(items[0], "watch"))}>
              {copy.viewHighlights}
            </button>
            <button className={view === "full" ? "on" : ""} onClick={() => {
              setView("full");
              setAuto(false);
              setSpeed(5);
            }}>{copy.viewFull}</button>
          </div>
          <select value={matchId} onChange={(e) => setMatchId(e.target.value)} aria-label="Match">
            {MATCHES.map((m) => (
              <option key={m.id} value={m.id}>{TEXT[`match_${m.id}`] ?? m.id}</option>
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
        <span className="side home">
          <span className="team home">{home.name}</span>
          {fastest(home.id)}
        </span>
        <span className="score">{sc.home}–{sc.away}</span>
        <span className="side away">
          <span className="team away">{away.name}</span>
          {fastest(away.id)}
        </span>
        <span className="clock">{clockLabel(data.meta, now)}</span>
      </div>

      {view === "highlights" && cur ? (
        <main className="grid">
          <section className="left">
            <div className="clip-head">
              <span className="clip-count muted small">{ix >= 0 ? `${ix + 1} / ${items.length}` : ""}</span>
              <strong>{label(cur)}</strong>
              <span className="muted">{cur.clock} · {who(cur)}</span>
              <span className={`step-chip ${step}`}>{step === "watch" ? copy.stepWatch : copy.stepReplay}</span>
            </div>
            <div className="pitch-wrap">
              <Pitch data={data} now={now} mode={mode} view={step} selected={selected}
                     favourite={favourite} allBatteries={false} item={cur} focus={null}
                     reachLabel={copy.reachLabel} flatLabel={copy.flatLabel} onSelect={setSelected} />
            </div>
            <p className={`clip-caption ${cur.team}`}>{cur.caption}</p>
            {cur.reach && <p className="muted small">{copy.legendReach}</p>}
            <div className="clip-controls">
              <button onClick={() => prev && start(prev, "watch")} disabled={!prev}>{copy.prev}</button>
              <div className="toggle" role="group" aria-label="Step">
                <button className={step === "watch" ? "on" : ""} onClick={() => start(cur, "watch")}>
                  {copy.stepWatch}
                </button>
                <button className={step === "replay" ? "on" : ""} onClick={() => start(cur, "replay")}>
                  {copy.stepReplay}
                </button>
              </div>
              <button onClick={() => setPlaying((p) => !p)} aria-label={playing ? "Pause" : "Play"}>
                {playing ? "Pause" : "Play"}
              </button>
              <button className={`next${!playing && step === "replay" ? " ready" : ""}`}
                      onClick={() => next && start(next, "watch")} disabled={!next}>{copy.next}</button>
            </div>
          </section>
          <aside className="right">
            {step === "replay" ? (
              <>
                <Replay data={data} item={cur} now={now} mode={mode} name={who(cur) ?? ""}
                        text={TEXT} onSeek={(v) => { setNow(v); setPlaying(false); }} />
                {!cur.player && (
                  <TeamChart meta={data.meta} now={now} title={copy.teamChart} sub={copy.teamChartSub}
                             yTitle={copy.teamChartAxis} onSeek={setNow} />
                )}
                {!cur.player && (() => {
                  // The team moment's 15-min block (its key second is the block's last).
                  const b = data.meta.team_situations.find((x) => x.video_start <= cur.at
                                                                  && cur.at < x.video_end);
                  return b ? <SplitChart meta={data.meta} blocks={[b]} text={TEXT}
                                         scope={fill(copy.splitBlock, { block: `${b.from}–${b.to}` })} />
                    : null;
                })()}
              </>
            ) : (
              <section className="up-next card">
                <h3>{copy.upNext}</h3>
                <ol>
                  {items.map((it) => (
                    <li key={it.id}>
                      <button className={`up-item${it.id === cur.id ? " on" : ""}`}
                              onClick={() => start(it, "watch")}>
                        <span className={`dot ${it.team}`} aria-hidden="true" />
                        <span className="up-label">{label(it)}</span>
                        <span className="up-who">{who(it)}</span>
                        <span className="muted">{it.clock}</span>
                      </button>
                    </li>
                  ))}
                </ol>
              </section>
            )}
          </aside>
        </main>
      ) : (
        <main className="grid">
          <section className="left">
            <div className="pitch-wrap">
              <Pitch data={data} now={now} mode={mode} view="full" selected={selected}
                     favourite={favourite} allBatteries={allBatteries} item={null} focus={focus}
                     reachLabel={copy.reachLabel} flatLabel={copy.flatLabel} onSelect={setSelected} />
            </div>
            {momentLine && (
              <p className={`clip-caption ${momentLine.team}`} aria-live="polite">
                <strong>{KIND[momentLine.kind] ?? momentLine.kind}</strong> {momentLine.sentence}
              </p>
            )}
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
            <Legend mode={mode} text={TEXT} allBatteries={allBatteries}
                    onAllBatteries={setAllBatteries} />
            <div className="moments">
              {data.feed.moments.map((m) => (
                <button key={m.moment_id} className="chip" onClick={() => setNow(m.video_s - 3)}>
                  {m.clock} {KIND[m.kind] ?? m.kind}
                </button>
              ))}
            </div>
            <Highlights all={data.highlights} meta={data.meta} now={now} active={null}
                        reelOn={false} text={TEXT} onPick={(h) => start(itemOfHighlight(h), "watch")}
                        onReel={() => {
                          if (!items.length) return;
                          setAuto(true);
                          start(items[0], "watch");
                        }} />
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
                    <p>{fill(copy.topSpeed, topSpeed(sel.name, s.speed, i))}</p>
                    {s.red_zone[i] ? <p>{fill(copy.redZone, { name: sel.name })}</p>
                      : s.post_peak[i] ? <p>{fill(copy.postPeak, { name: sel.name })}</p> : null}
                  </>
                )
              ) : (
                <p className="muted">Click a player on the pitch.</p>
              )}
            </div>
            <TeamChart meta={data.meta} now={now} title={copy.teamChart} sub={copy.teamChartSub}
                       yTitle={copy.teamChartAxis} onSeek={setNow} />
            <SplitChart meta={data.meta} text={TEXT} scope={copy.splitSoFar}
                        blocks={data.meta.team_situations.filter((b) => b.video_end <= now + 0.5)} />
            {mode === "analyst" && sel && s && (
              <Trace signals={s} meta={data.meta} now={now} name={sel.name} text={TEXT}
                     onSeek={setNow} />
            )}
          </section>
          <aside className="right">
            <Feed feed={data.feed} meta={data.meta} now={now} mode={mode} favourite={favourite}
                  showBlocked={showBlocked} onShowBlocked={setShowBlocked} onSeek={(v, p) => {
                    setNow(v);
                    if (p) setSelected(p);
                  }} blockedNote={copy.blocked} />
          </aside>
        </main>
      )}
      <p className="muted small">{copy.disclaimer}</p>
    </div>
  );
}

function topSpeed(name: string, speed: number[], i: number) {
  let top = 0;
  for (let k = 0; k <= i; k++) if (speed[k] <= 110 && speed[k] > top) top = speed[k];
  return { name, v: (top / 10).toFixed(1), kmh: Math.round(top * 0.36) };
}

// Moment names on screen, in the words English football uses (copy.json "kind_*"; the
// Verifier checks them with the rest of the copy).
export const KIND: Record<string, string> = Object.fromEntries(
  Object.entries(TEXT).filter(([k]) => k.startsWith("kind_")).map(([k, v]) => [k.slice(5), v]),
);
