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
import { BrandMark, LowerThird, TeamSheet, reading } from "./Battery";
import { Feed } from "./Feed";
import { Highlights, reel } from "./Highlights";
import { Legend, Pitch } from "./Pitch";
import { Replay } from "./Replay";
import { SplitChart } from "./SplitChart";
import { TeamChart } from "./TeamChart";
import { Trace } from "./Trace";

const SPEEDS = [1, 5, 20];
const CLIP_SPEEDS = [0.5, 1, 2]; // a clip and its replay play at 1× unless the viewer picks another
const LAPSE_SPEED = 120; // most ground covered: the whole match in under a minute
const AUTO_DETAILS_MS = 6000; // "Play highlights": the details stay this long before the next clip
const FOCUS_BEFORE = 8; // full match: a feed moment is in focus from 8 s before to 6 s after
const FOCUS_AFTER = 6;
// Start state from the URL (for links and video capture): ?view=full&match=story&t=3500&
// mode=analyst&player=H04; the Highlights view takes ?hl=<kind> (the match's best of a kind),
// ?moment=<kind or moment id> (with &player=), or ?item=<n>, then &step=watch|details|replay
// (plays it, opens it finished with its details, or plays the replay) and &auto=1 (play the
// clips one after another). JOURNEY.md "Deep links" lists the screen and tab each one opens.
const QUERY = new URLSearchParams(window.location.search);
// Dark by default (DESIGN.md); ?theme=light or Settings › Theme for light.
const THEME = QUERY.get("theme") === "light" ? "light" : "dark";

type View = "highlights" | "full";
// Each clip plays once (watch), then shows its details on its last frame; Replay plays it
// again with the details growing (decision 34; at the clip speed since decision 37).
type Step = "watch" | "details" | "replay";
// The tabs under the pitch (decision 36); one open at a time.
type Tab = "clips" | "team" | "details" | "settings";
const TABS: [Tab, string][] = [
  ["clips", copy.tabClips], ["team", copy.tabTeam], ["details", copy.tabDetails],
  ["settings", copy.tabSettings],
];
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
    return list.find((i) => (i.momentId === m || i.momentKind === m) && (!p || i.player === p));
  }
  const n = Number(QUERY.get("item"));
  return Number.isInteger(n) && n >= 1 ? list[n - 1] : undefined;
}

/** A row of mutually exclusive choices (Settings). */
function Choice<T extends string>({ label, value, options, onPick }: {
  label: string;
  value: T;
  options: [T, string][];
  onPick: (v: T) => void;
}) {
  return (
    <div className="field">
      <span className="field-label">{label}</span>
      <div className="choice" role="group" aria-label={label}>
        {options.map(([v, l]) => (
          <button key={v} className={value === v ? "on" : ""} aria-pressed={value === v}
                  onClick={() => onPick(v)}>{l}</button>
        ))}
      </div>
    </div>
  );
}

export default function App() {
  const [matchId, setMatchId] = useState(QUERY.get("match") ?? MATCHES[0].id);
  const [data, setData] = useState<MatchData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [view, setView] = useState<View>(QUERY.get("view") === "full" ? "full" : "highlights");
  const [now, setNow] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(5);
  const [clipSpeed, setClipSpeed] = useState(1);
  const [mode, setMode] = useState<Mode>(QUERY.get("mode") === "analyst" ? "analyst" : "fan");
  const [selected, setSelected] = useState<string | null>(null);
  const [favourite, setFavourite] = useState<string | null>(null);
  const [showBlocked, setShowBlocked] = useState(false);
  const [allBatteries, setAllBatteries] = useState(QUERY.get("batteries") === "all");
  const [cur, setCur] = useState<Item | null>(null);
  const [step, setStep] = useState<Step>("watch");
  const [auto, setAuto] = useState(QUERY.get("auto") === "1");
  const [theme, setTheme] = useState<"dark" | "light">(THEME);
  const [tab, setTab] = useState<Tab>(QUERY.get("view") === "full" ? "details" : "clips");
  // Tab rules (JOURNEY.md): a clip's end borrows the Details tab and the next clip hands back
  // the tab the viewer was on; a tab the viewer picks during a clip is never changed for them.
  const back = useRef<Tab | null>(null);
  const picked = useRef(false);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
  }, [theme]);

  const items = useMemo(
    () => (data ? queue(data, mode, reel(data.highlights, data.duration)) : []),
    [data, mode],
  );

  const borrowDetails = () => {
    if (picked.current) return;
    setTab((t) => {
      if (t !== "details") back.current = t;
      return "details";
    });
  };
  const pickTab = (t: Tab) => {
    picked.current = true;
    back.current = null;
    setTab(t);
  };

  // Play a clip (watch, replay), or open it finished with its details.
  const start = (it: Item, st: Step) => {
    setCur(it);
    setStep(st);
    setView("highlights");
    if (it.player) setSelected(it.player);
    if (st === "details") {
      setNow(it.lapse ? it.end : it.end + 2);
      setPlaying(false);
    } else {
      setNow(clipFrom(it));
      setSpeed(it.lapse ? LAPSE_SPEED : clipSpeed);
      setPlaying(true);
    }
    if (st === "watch") {
      picked.current = false;
      if (back.current) {
        setTab(back.current);
        back.current = null;
      }
    } else {
      borrowDetails();
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
        const fav = QUERY.get("favourite") ?? d.feed.favourite ?? null;
        setFavourite(fav);
        const list = queue(d, mode, reel(d.highlights, d.duration));
        const defaultItem = list.find((i) => i.momentId && (!fav || i.player === fav))
          ?? list.find((i) => i.momentId) ?? list[0];
        const it = view === "highlights" ? itemFromUrl(d, list) ?? defaultItem : undefined;
        if (it) {
          const st = QUERY.get("step");
          start(it, st === "replay" || st === "details" ? st : "watch");
          if (hasT) setNow(t);
        } else if (view === "highlights") {
          setView("full"); // no clips in this mode: open the full match
          setTab("details");
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

  // Previous and Next follow match time, so they work for a clip that is not in the list too.
  const ix = cur ? items.findIndex((i) => i.id === cur.id) : -1;
  const next = cur ? (ix >= 0 ? items[ix + 1] : items.find((i) => i.at > cur.at)) : items[0];
  const prev = cur
    ? (ix >= 0 ? items[ix - 1] : [...items].reverse().find((i) => i.at < cur.at))
    : undefined;

  // When the clip (or its replay) is over, stop on its last frame with the details.
  useEffect(() => {
    if (view !== "highlights" || !cur || !playing || !data) return;
    if (now < clipTo(cur, data.duration)) return;
    setPlaying(false);
    setStep("details");
    borrowDetails();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [now, playing]);
  // "Play highlights": the details stay a few seconds, then the next clip.
  useEffect(() => {
    if (view !== "highlights" || !auto || step !== "details") return;
    const id = setTimeout(() => (next ? start(next, "watch") : setAuto(false)), AUTO_DETAILS_MS);
    return () => clearTimeout(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [auto, step, cur, view]);

  const players = useMemo(
    () => (data ? Object.fromEntries(data.meta.players.map((p) => [p.id, p])) : {}),
    [data],
  );
  // Each player's fastest second so far, second by second (for "Fastest so far").
  const topSoFarBy = useMemo(() => {
    if (!data) return {};
    return Object.fromEntries(Object.entries(data.signals).map(([id, s]) => {
      let top = 0;
      return [id, s.speed.map((v) => (top = v <= 110 && v > top ? v : top))];
    }));
  }, [data]);

  if (error) return <div className="app"><p className="sub">{copy.loadError}</p></div>;
  if (!data) return <div className="app"><p className="sub">{copy.loading}</p></div>;

  const sc = score(data.meta, now);
  const [home, away] = data.meta.teams;
  const sel = selected ? players[selected] : null;
  const s = selected ? data.signals[selected] : undefined;
  const i = signalIndex(s, now);

  const fastest = (team: { id: string; name: string }) => {
    let best: { name: string; v: number } | null = null;
    for (const p of data.meta.players) {
      const sp = data.signals[p.id];
      const tops = topSoFarBy[p.id];
      if (p.team !== team.id || !sp || !tops || p.position === "GK") continue;
      const k = Math.min(Math.floor(now - sp.start), tops.length - 1);
      if (k < 0) continue;
      if (!best || tops[k] > best.v) best = { name: p.name, v: tops[k] };
    }
    return best && best.v > 0 ? (
      <li key={team.id}><span className={`dot ${team.id}`} aria-hidden="true" />
        <span className="num">{fill(copy.fastestTeam, {
          team: team.name, name: best.name, v: (best.v / 10).toFixed(1), kmh: Math.round(best.v * 0.36),
        })}</span></li>
    ) : null;
  };

  // Full match: the feed moment on screen and its player.
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

  // The latest finished 5-minute block of both teams' running (for a team moment's lower third).
  const block = [...data.meta.team_running].reverse().find((b) => b.video_end <= now + 0.5) ?? null;
  const blockLabel = block
    ? `${clockLabel(data.meta, block.video_start)}–${clockLabel(data.meta, block.video_end)}` : "";
  const lowerThird = (tag: string, clock: string, team: string, whoName: string, pid?: string) => {
    const p = pid ? players[pid] : undefined;
    return (
      <LowerThird tag={tag} clock={clock} team={team} who={whoName} player={p}
                  r={reading(data, p, now)} offPitch={!!p && signalIndex(data.signals[p.id], now) === null}
                  mode={mode} text={TEXT} teamRun={block} blockLabel={blockLabel} teams={data.meta.teams} />
    );
  };

  const toFull = () => {
    setView("full");
    setAuto(false);
    setSpeed(5);
  };
  // Dragging a finished clip back plays its end again as a replay (the details grow with it).
  const seekClip = (v: number) => {
    setNow(v);
    if (cur && step === "details" && v < clipTo(cur, data.duration)) {
      setStep("replay");
      borrowDetails();
    }
  };
  const toHighlights = () => (cur ? start(cur, "watch") : items[0] && start(items[0], "watch"));
  const stepName = step === "watch" ? copy.stepWatch : step === "replay" ? copy.stepReplay : copy.stepDetails;
  const band = mode === "analyst" && cur?.player ? reading(data, players[cur.player], now) : null;

  const hasBlocked = (it: Item) =>
    Boolean(it.momentId && data.feed.entries.some(
      (e) => e.moment_id === it.momentId && e.mode === mode && e.verdict === "blocked",
    ));
  const clipRow = (it: Item, n: number | null) => (
    <li key={`${it.id}-${n ?? "x"}`}>
      <button className={`clip-row${cur && it.id === cur.id ? " on" : ""}`}
              onClick={() => start(it, "watch")}>
        <span className="clip-n num">{n ?? ""}</span>
        <span className={`dot ${it.team}`} aria-hidden="true" />
        <span className="clip-kind">{label(it)}</span>
        <span className="clip-who">{who(it)}</span>
        <span className="clip-clock num">{it.clock}</span>
        <span className="clip-now">
          {cur && it.id === cur.id ? copy.nowPlaying : hasBlocked(it) ? copy.clipBlocked : ""}
        </span>
      </button>
    </li>
  );

  return (
    <div className="app">
      <header className="masthead">
        <div className="bug" aria-label={`${home.name} ${sc.home}, ${away.name} ${sc.away}`}>
          <span className="bug-team"><span className="chip home" aria-hidden="true" />
            <span className="full">{home.name}</span><span className="code">{code(home.name)}</span></span>
          <span className="bug-score num">{sc.home}–{sc.away}</span>
          <span className="bug-team"><span className="full">{away.name}</span>
            <span className="code">{code(away.name)}</span><span className="chip away" aria-hidden="true" /></span>
          <span className="bug-clock num">{clockLabel(data.meta, now)}</span>
        </div>
        <div className="brand">
          <p className="brand-name"><BrandMark /><strong>{copy.brand}</strong>
            <span className="brand-syn">· {copy.brandSynthetic}</span></p>
          <p className="tagline">{copy.tagline}</p>
        </div>
      </header>

      <div className="frame">
        <div className="pitch-wrap">
          {view === "highlights" && cur ? (
            <Pitch data={data} now={now} mode={mode} view={step === "watch" ? "watch" : "replay"}
                   selected={selected} favourite={favourite} allBatteries={false} item={cur} focus={null}
                   flatLabel={copy.flatLabel} onSelect={setSelected} />
          ) : (
            <Pitch data={data} now={now} mode={mode} view="full" selected={selected}
                   favourite={favourite} allBatteries={allBatteries} item={null} focus={focus}
                   flatLabel={copy.flatLabel} onSelect={setSelected} />
          )}
          {view === "highlights" && step === "details" && <span className="pitch-flag">{copy.clipEnded}</span>}
        </div>

        {view === "highlights" && cur
          ? lowerThird(label(cur), cur.clock, cur.team, who(cur) ?? "", cur.player ?? undefined)
          : momentLine
            ? lowerThird(KIND[momentLine.kind] ?? momentLine.kind, momentLine.clock, momentLine.team,
                         momentLine.team_name, momentLine.player?.id)
            : sel && lowerThird(copy.ltFollow, clockLabel(data.meta, now), sel.team, sel.name, sel.id)}

        {view === "highlights" && cur ? (
          <div className="playbar clip-bar">
            <div className="scrub">
              <input type="range" min={clipFrom(cur)} max={clipTo(cur, data.duration)} step={cur.lapse ? 1 : 0.1}
                     value={Math.min(Math.max(now, clipFrom(cur)), clipTo(cur, data.duration))}
                     onChange={(e) => seekClip(Number(e.target.value))} aria-label={copy.clipTime} />
              <span className="time num">
                {mmss(now - clipFrom(cur))} / {mmss(clipTo(cur, data.duration) - clipFrom(cur))}
              </span>
            </div>
            <div className="controls">
              <button onClick={() => prev && start(prev, "watch")} disabled={!prev}>{copy.prev}</button>
              <button className={step === "details" ? "outline" : ""}
                      onClick={() => start(cur, "replay")}>{copy.replayButton}</button>
              <button onClick={() => (step === "details" ? start(cur, "replay") : setPlaying((p) => !p))}>
                {playing ? copy.pause : copy.play}
              </button>
              <button className={step === "details" ? "outline" : ""}
                      onClick={() => next && start(next, "watch")} disabled={!next}>{copy.next}</button>
              {!cur.lapse && (
                <div className="speeds" role="group" aria-label={copy.speed}>
                  {CLIP_SPEEDS.map((x) => (
                    <button key={x} className={clipSpeed === x ? "on" : ""} aria-pressed={clipSpeed === x}
                            onClick={() => { setClipSpeed(x); setSpeed(x); }}>
                      <span className="num">{x === 0.5 ? "½" : x}×</span>
                    </button>
                  ))}
                </div>
              )}
              <span className="status num">{stepName}{ix >= 0 ? ` · ${ix + 1} / ${items.length}` : ""}</span>
            </div>
          </div>
        ) : (
          <div className="playbar transport">
            <button onClick={() => setPlaying((p) => !p)}>{playing ? copy.pause : copy.play}</button>
            <input type="range" min={0} max={data.duration - 1} step={1} value={now}
                   onChange={(e) => setNow(Number(e.target.value))} aria-label={copy.matchTime} />
            <div className="speeds" role="group" aria-label={copy.speed}>
              {SPEEDS.map((x) => (
                <button key={x} className={speed === x ? "on" : ""} aria-pressed={speed === x}
                        onClick={() => setSpeed(x)}><span className="num">{x}×</span></button>
              ))}
            </div>
          </div>
        )}
      </div>

      <nav className="tabs" role="tablist">
        {TABS.map(([t, l]) => (
          <button key={t} role="tab" aria-selected={tab === t} className={tab === t ? "on" : ""}
                  onClick={() => pickTab(t)}>{l}</button>
        ))}
      </nav>

      <section className="panel" role="tabpanel">
        {tab === "clips" && (
          <div className="clips">
            <ul className="fastest">{fastest(home)}{fastest(away)}</ul>
            {view === "highlights" ? (
              <>
                <button className="link" onClick={toFull}>{copy.viewFull}</button>
                <h3>{copy.upNext}</h3>
                <ol className="clip-list">
                  {cur && ix < 0 && clipRow(cur, null)}
                  {items.map((it, k) => clipRow(it, k + 1))}
                </ol>
              </>
            ) : (
              <>
                <button className="link" onClick={toHighlights}>{copy.viewHighlights}</button>
                <div className="moments">
                  {data.feed.moments.map((m) => (
                    <button key={m.moment_id} className="moment" onClick={() => setNow(m.video_s - 3)}>
                      <span className="num">{m.clock}</span> {KIND[m.kind] ?? m.kind}
                    </button>
                  ))}
                </div>
                <Highlights all={data.highlights} meta={data.meta} now={now} text={TEXT}
                            onPick={(h) => start(itemOfHighlight(h), "watch")}
                            onReel={() => {
                              if (!items.length) return;
                              setAuto(true);
                              start(items[0], "watch");
                            }} />
              </>
            )}
          </div>
        )}

        {tab === "team" && (
          <div className="team">
            {view === "full" && (
              <div className="player-card">
                {sel ? (
                  i === null || !s ? (
                    <p>{fill(copy.offPitch, { name: sel.name })}</p>
                  ) : (
                    <>
                      <h3><span className="num">{sel.shirt}</span> {sel.name}
                        <span className="sub"> {sel.position}, {sel.team_name}</span></h3>
                      <p className="num">{fill(copy.battery, { name: sel.name, pct: s.battery[i] })}</p>
                      {mode === "analyst" && s.lo && s.hi && (
                        <p className="sub num">{fill(copy.band, { lo: s.lo[i], hi: s.hi[i] })}</p>
                      )}
                      {mode === "analyst" && s.low_chance && (
                        <p className="sub num">{fill(copy.lowChance, {
                          chance: s.low_chance[i] < 1 ? "less than 1%" : `about ${s.low_chance[i]}%`,
                        })}</p>
                      )}
                      <p className="num">{fill(copy.topSpeed, topSpeed(sel.name, s.speed, i))}</p>
                      {s.red_zone[i] ? <p>{fill(copy.redZone, { name: sel.name })}</p>
                        : s.post_peak[i] ? <p>{fill(copy.postPeak, { name: sel.name })}</p> : null}
                    </>
                  )
                ) : (
                  <p className="sub">{copy.clickPlayer}</p>
                )}
                {mode === "analyst" && sel && s && (
                  <Trace signals={s} meta={data.meta} now={now} name={sel.name} text={TEXT}
                         onSeek={setNow} />
                )}
              </div>
            )}
            <TeamSheet data={data} now={now} mode={mode}
                       on={view === "highlights" ? cur?.player ?? null : selected} favourite={favourite}
                       text={TEXT} onSelect={(id) => {
                         setSelected(id);
                         if (view === "highlights") toFull();
                       }} />
            <TeamChart meta={data.meta} now={now} title={copy.teamChart} sub={copy.teamChartSub}
                       yTitle={copy.teamChartAxis} onSeek={setNow} />
            <SplitChart meta={data.meta} text={TEXT} scope={copy.splitSoFar}
                        blocks={data.meta.team_situations.filter((b) => b.video_end <= now + 0.5)} />
          </div>
        )}

        {tab === "details" && (
          view === "highlights" && cur ? (
            step === "watch" ? <p className="sub">{copy.detailsWait}</p> : (
              <>
                <Replay data={data} item={cur} now={now} mode={mode} name={who(cur) ?? ""}
                        replaying={step === "replay"}
                        band={band && band.lo !== null ? fill(copy.ltBand, { lo: band.lo, hi: band.hi ?? "" }) : null}
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
            )
          ) : (
            <Feed feed={data.feed} now={now} mode={mode} favourite={favourite} text={TEXT}
                  showBlocked={showBlocked} onShowBlocked={setShowBlocked} onSeek={(v, p) => {
                    setNow(v);
                    if (p) setSelected(p);
                  }} />
          )
        )}

        {tab === "settings" && (
          <div className="settings">
            <Choice label={copy.settingsView} value={view}
                    options={[["highlights", copy.viewHighlights], ["full", copy.viewFull]]}
                    onPick={(v) => (v === "full" ? toFull() : toHighlights())} />
            <Choice label={copy.settingsAudience} value={mode}
                    options={[["fan", copy.fan], ["analyst", copy.analyst]]} onPick={setMode} />
            <label className="field">
              <span className="field-label">{copy.settingsMatch}</span>
              <select value={matchId} onChange={(e) => setMatchId(e.target.value)}>
                {MATCHES.map((m) => (
                  <option key={m.id} value={m.id}>{TEXT[`match_${m.id}`] ?? m.id}</option>
                ))}
              </select>
            </label>
            <label className="field">
              <span className="field-label">{copy.settingsFavourite}</span>
              <select value={favourite ?? ""} onChange={(e) => setFavourite(e.target.value || null)}>
                <option value="">{copy.favouriteNone}</option>
                {data.meta.teams.map((t) => (
                  <optgroup key={t.id} label={t.name}>
                    {data.meta.players.filter((p) => p.team === t.id).map((p) => (
                      <option key={p.id} value={p.id}>{p.shirt} {p.name}</option>
                    ))}
                  </optgroup>
                ))}
              </select>
            </label>
            <Choice label={copy.settingsTheme} value={theme}
                    options={[["dark", copy.themeDark], ["light", copy.themeLight]]} onPick={setTheme} />
            {view === "full" && mode === "fan" && (
              <div className="field">
                <span className="field-label">{copy.settingsPitch}</span>
                <label className="check">
                  <input type="checkbox" checked={allBatteries}
                         onChange={(e) => setAllBatteries(e.target.checked)} />
                  {allBatteries ? copy.batteriesAll : copy.batteriesSome}
                </label>
              </div>
            )}
            <Legend mode={mode} text={TEXT} />
          </div>
        )}
      </section>

      <footer className="footer">{copy.disclaimer}</footer>
    </div>
  );
}

/** A clip plays from 3 s before its first run to 2 s after its end; a whole-match clip from
 * kick-off to its end. */
function clipFrom(it: Item) {
  return it.lapse ? 0 : Math.max(it.start - 3, 0);
}
function clipTo(it: Item, duration: number) {
  return Math.min(it.lapse ? it.end : it.end + 2, duration - 1);
}

/** Seconds as m:ss. */
function mmss(s: number) {
  const t = Math.max(Math.round(s), 0);
  return `${Math.floor(t / 60)}:${String(t % 60).padStart(2, "0")}`;
}

/** A team's three-letter code for the score bug on a phone ("Westerlyn Albion" → "WES"). */
function code(name: string) {
  return name.slice(0, 3).toUpperCase();
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
