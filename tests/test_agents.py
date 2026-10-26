"""MCP tools, server and feed (BUILD_PLAN "Wed 21"–"Thu 22") on a constructed match: each tool's
output shape, the moments it must find, the context reasons, and that nothing in agents/ can
read the truth. Constructed inputs only (the same seed gives a different match elsewhere); no
LLM calls (the feed runs offline)."""

import ast
import asyncio
import builtins
import io
import json
import re
from pathlib import Path

import numpy as np
import pytest

from runningbattery.agents import feed as feed_mod
from runningbattery.agents.tools import MOMENT_KINDS, MatchTools, clock_label, parse_time
from runningbattery.agents.verifier import verify
from runningbattery.engine.estimate import estimate
from runningbattery.io import SIGNALS, Match, write_match, write_signals
from runningbattery.schema import (
    Ball,
    Event,
    Generator,
    MatchMetadata,
    PeriodInfo,
    PlayerInfo,
    PlayerPosition,
    Point,
    Score,
    Substitution,
    TeamInfo,
    TrackingFrame,
)

AGENTS = Path(__file__).resolve().parents[1] / "src" / "runningbattery" / "agents"
HZ = 10
DURATION = (900.0, 600.0)
POSITIONS = ["GK", "CB", "CB", "FB", "FB", "DM", "CM", "AM", "WM", "WM", "CF"]
SUB_T = 30.0  # H12 on for H11, 30 s into the second half
LOST = (200.0, 260.0)  # period 1: away have the ball (home just lost it at 200 s)
DEAD = (300.0, 360.0)  # period 2: a one-minute stoppage


def _speed(pid: str, period: int, t: float) -> float:
    """Who runs, when: H04 (left-back) an intense minute at 7.5 m/s, then another later (back
    to his normal, and near his top speed); A04 (the away left-back) a minute at
    6 m/s; H12 (the substitute) two minutes at 6 m/s."""
    if pid == "H04" and period == 1 and (60.0 <= t < 120.0):
        return 7.5
    if pid == "H04" and period == 1 and (700.0 <= t < 760.0):
        return 7.5  # the first run's top is a little higher: he steps onto the circle
    if pid == "A04" and period == 1 and (300.0 <= t < 360.0):
        return 6.0
    if pid == "H12" and period == 2 and (60.0 <= t < 180.0):
        return 6.0
    return 0.0


def _team(side: str) -> TeamInfo:
    letter = side[0].upper()
    players = [
        PlayerInfo(id=f"{letter}{i:02d}", name=f"Player {letter}{i}", shirt=i, position=pos,
                   starter=True)
        for i, pos in enumerate(POSITIONS, start=1)
    ]  # fmt: skip
    players.append(PlayerInfo(id=f"{letter}12", name=f"Sub {letter}", shirt=12, position="CF",
                              starter=False))  # fmt: skip
    return TeamInfo(id=side, name=f"{side} FC", side=side, formation="4-2-3-1",
                    attacks_positive_x_in_period_1=side == "home", players=players)  # fmt: skip


def _event(i, period, t, type_, team, player, score, **kw) -> Event:
    return Event(id=i, period=period, t=t, clock=t + (2700.0 if period == 2 else 0.0),
                 type=type_, team_id=team, player_id=player,
                 score=Score(home=score[0], away=score[1]), **kw)  # fmt: skip


def _match() -> Match:
    teams = [_team("home"), _team("away")]
    starters = [p.id for team in teams for p in team.players if p.starter]
    spots = {pid: (-40.0 + 4.0 * k, -30.0 + 2.5 * k) for k, pid in enumerate(starters)}
    angle = {pid: 0.0 for pid in [*starters, "H12"]}
    frames, frame = [], 0
    for period, duration in enumerate(DURATION, start=1):
        for k in range(round(duration * HZ)):
            t = round(k / HZ, 1)
            players = []
            for pid in starters:
                if pid == "H11" and period == 2 and t >= SUB_T:
                    pid = "H12"
                v = _speed(pid, period, t)
                angle[pid] += v / HZ / 15.0
                x, y = spots["H11" if pid == "H12" else pid]
                if v or angle[pid]:  # runners circle the centre spot (15 m radius)
                    x, y = 15.0 * np.cos(angle[pid]), 15.0 * np.sin(angle[pid])
                players.append(PlayerPosition(id=pid, x=round(x, 2), y=round(y, 2)))
            dead = period == 2 and DEAD[0] <= t < DEAD[1]
            away = period == 1 and LOST[0] <= t < LOST[1]
            frames.append(TrackingFrame(
                frame=frame, period=period, t=t, clock=t + (2700.0 if period == 2 else 0.0),
                ball_status="dead" if dead else "alive",
                possession_team="away" if away else "home",
                ball=Ball(x=0.0, y=0.0, z=0.0), players=players,
            ))  # fmt: skip
            frame += 1
    n1 = round(DURATION[0] * HZ)
    events = [
        _event(0, 1, 100.0, "goal", "home", "H11", (0, 0), possession_id=1),
        _event(1, 1, 200.5, "pass", "away", "A08", (1, 0), possession_id=2,
               phase="positive_transition", start=Point(x=0.0, y=0.0)),
        _event(2, 1, 205.0, "shot", "away", "A11", (1, 0), possession_id=2, phase="final_third",
               xg=0.3),
        _event(3, 2, SUB_T, "substitution", "home", "H11", (1, 0), related_player_id="H12"),
        _event(4, 2, 50.0, "goal", "home", "H10", (1, 0), possession_id=3),
    ]  # fmt: skip
    meta = MatchMetadata(
        match_id="constructed",
        generator=Generator(version="test", seed=0),
        periods=[
            PeriodInfo(period=1, start_frame=0, end_frame=n1 - 1, duration_s=DURATION[0]),
            PeriodInfo(period=2, start_frame=n1, end_frame=frame - 1, duration_s=DURATION[1]),
        ],
        teams=teams,
        substitutions=[
            Substitution(period=2, t=SUB_T, team_id="home", player_out="H11", player_in="H12")
        ],
    )
    return Match(metadata=meta, frames=frames, events=events)


@pytest.fixture(scope="module")
def folder(tmp_path_factory) -> Path:
    path = tmp_path_factory.mktemp("match")
    m = _match()
    write_match(path, m.metadata, m.frames, m.events)
    write_signals(path / SIGNALS, estimate(m))
    (path / "truth.json").write_text(json.dumps({"secret": True}))
    return path


@pytest.fixture(scope="module")
def tools(folder) -> MatchTools:
    return MatchTools(folder)


def _numbers_have_units(obj, path="") -> None:
    """Every {"value": …} carries a unit and a source."""
    if isinstance(obj, dict):
        if "value" in obj and isinstance(obj["value"], int | float):
            assert {"unit", "source"} <= obj.keys(), path
        for k, v in obj.items():
            _numbers_have_units(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            _numbers_have_units(v, f"{path}[{i}]")


def test_clock_labels_and_parsing():
    assert clock_label(1, 2830.0) == "45+2:10" and parse_time("45+2:10") == (1, 2830.0)
    assert clock_label(2, 1332.0) == "67:12" and parse_time("67:12") == (2, 1332.0)
    assert parse_time("20:00") == (1, 1200.0) and parse_time(67.2)[0] == 2
    assert clock_label(2, 2760.0) == "90+1:00"


def test_match_summary(tools):
    s = tools.match_summary()
    assert s["synthetic"] and [t["id"] for t in s["teams"]] == ["home", "away"]
    assert s["final_score"] == {"home": 2, "away": 0}
    assert [g["score"] for g in s["goals"]] == [{"home": 1, "away": 0}, {"home": 2, "away": 0}]
    assert s["substitutions"][0] | {} and s["substitutions"][0]["on_id"] == "H12"
    assert s["substitutions"][0]["clock"] == "45:30"
    _numbers_have_units(s)


def test_player_signals_shape(tools):
    p = tools.player_signals("H04", "0:00", "3:00")
    assert p["on_pitch"] and p["player"]["position"] == "FB"
    assert set(p) >= {"battery", "low_chance", "energy", "hsr", "flags", "in_play"}
    assert 0.0 <= p["battery"]["typical_pro_at_end"]["value"] <= 1.0
    assert p["flags"]["hardest_minutes_count"]["value"] >= 1
    assert "typical professional" in p["battery"]["note"]
    assert "calibration" in p["low_chance"]["calibration"].lower()
    _numbers_have_units(p)
    assert tools.player_signals("home 4")["player"]["id"] == "H04"  # team and shirt
    assert tools.player_signals("H12", "0:00", "10:00")["on_pitch"] is False  # not on yet


def test_find_moments(tools):
    for kind in MOMENT_KINDS:
        r = tools.find_moments(kind, 5)
        assert r["kind"] == kind and r["claims"] and isinstance(r["moments"], list)
        assert [m["rank"] for m in r["moments"]] == list(range(1, len(r["moments"]) + 1))
        for m in r["moments"]:
            assert {"id", "period", "t", "clock", "video_s", "player", "facts"} <= m.keys()
            _numbers_have_units(m["facts"])
    red = tools.find_moments("red_zone")["moments"]
    assert red and red[0]["player"]["id"] == "H04" and red[0]["period"] == 1
    # The turnover at 200.5 s comes 200 s into his match, under SO_FAR_MIN_S: "just after his
    # hardest minutes so far" would be true of almost any running (decision 42).
    assert not tools.find_moments("exposed_on_turnover", player="H04")["moments"]
    back = tools.find_moments("second_wind", player="H04")["moments"]
    assert back and 700.0 <= back[0]["t"] <= 760.0  # back to his normal on the second run
    fresh = tools.find_moments("fresh_legs")["moments"]
    assert [m["player"]["id"] for m in fresh] == ["H12"]
    assert fresh[0]["facts"]["sub_hsr_per_min"]["value"] > 0
    assert fresh[0]["facts"]["vs_teammates"]["value"] is None  # team-mates stood still: no ratio
    assert "error" in tools.find_moments("tired")


def test_team_running_and_tug_of_war(tools):
    r = tools.team_running()
    home, away = r["teams"]["home"], r["teams"]["away"]
    assert home["hsr_per_in_play_min"]["value"] > away["hsr_per_in_play_min"]["value"] > 0
    assert [b["period"] for b in r["blocks"]] == [1, 2] and "claim 35" in r["note"]
    _numbers_have_units(r)
    tug = tools.find_moments("tug_of_war")["moments"]
    assert tug and tug[0]["player"] is None and tug[0]["team"]["id"] == "home"
    assert tug[0]["opponent"] == {"id": "away", "name": "away FC"}
    assert (
        tug[0]["facts"]["pattern"] == "ran harder" and tug[0]["facts"]["vs_opponent"]["value"] > 15
    )
    assert tools.find_moments("tug_of_war", player="H04")["moments"] == []  # team moments only


def test_flat_out_is_near_his_top_speed_so_far(tools, monkeypatch):
    """H04's second run reaches 94% of his first: before the 75th minute that is no moment
    (decision 39: below FLAT_OUT_EARLY_SHARE); at the 90% bar it is, with these facts."""
    import runningbattery.agents.tools as T

    assert tools.find_moments("flat_out", player="H04")["moments"] == []
    monkeypatch.setattr(T, "FLAT_OUT_EARLY_SHARE", T.FLAT_OUT_SHARE)
    flat = tools.find_moments("flat_out", player="H04")["moments"]
    assert flat and 700.0 <= flat[0]["t"] <= 760.0
    f = flat[0]["facts"]
    assert 90 <= f["share_of_top_speed"]["value"] <= 100 and not f["his_fastest_so_far"]
    assert (
        f["peak_speed_kmh"]["value"] == round(f["peak_speed"]["value"] * 3.6)
        or abs(f["peak_speed_kmh"]["value"] - f["peak_speed"]["value"] * 3.6) < 1
    )
    assert "SilvaH2025" in f["published_match_peak_for_position"]["source"]


def test_hardest_minutes_spells_close_together_count_once():
    """Decision 39: spells less than EPISODE_GAP_S apart in a half are one time ("for the eighth
    time" at 19:50 was a flickering flag); a new half starts a new one."""
    from types import SimpleNamespace

    from runningbattery.agents.tools import EPISODE_GAP_S, episodes

    t = np.array([0, 10, 20, 30, 100, 300, 5], float)
    s = SimpleNamespace(t=t, period=np.array([1, 1, 1, 1, 1, 1, 2]))
    spells = [(0, 1), (2, 3), (4, 4), (5, 5), (6, 6)]  # gaps 10, 70, 200 s, then half 2
    assert EPISODE_GAP_S == 60.0
    assert episodes(spells, s) == [1, 1, 2, 3, 4]


def test_touches_are_measured_and_gate_claim_14(tools):
    """Decision 25: touch counts from events.jsonl; claim 14 only when touches fell while the ball
    was out of play more than usual."""
    assert tools.m.touches == {"A08": [(1, 200.5)], "A11": [(1, 205.0)]}  # a pass and a shot
    s = tools.m.series["A11"]
    f = tools._touch_facts("A11", s.index(1, 400.0))
    assert f["touches_last_5min"]["value"] == 1 and not f["fewer_touches_than_usual"]
    f = tools._touch_facts("A11", s.index(1, 600.0))  # the shot is more than 5 min ago
    assert f["touches_last_5min"]["value"] == 0 and f["fewer_touches_than_usual"]
    assert not f["less_ball_in_play_than_usual"]  # the ball was never dead in the first half
    _numbers_have_units(f)
    for mo in tools.find_moments("not_tired_tactical", 50)["moments"]:
        fewer = mo["facts"]["fewer_touches_than_usual"]
        assert ("14" in mo["claims"]) == (fewer and mo["facts"]["less_ball_in_play_than_usual"])


def test_moment_context_reasons(tools):
    ctx = tools.moment_context("50:30", 2, team="home")  # 330 s into the half: stoppage, 2–0
    codes = {r["code"] for r in ctx["non_fatigue_reasons"]}
    assert not ctx["ball_in_play"] and ctx["ball_out_for"]["value"] >= 30
    assert {"ball_out_of_play", "big_lead", "start_of_half"} <= codes
    sub = tools.moment_context(46.5, 2, "H12")  # 90 s into the half, on for 60 s
    assert "just_subbed_on" in {r["code"] for r in sub["non_fatigue_reasons"]}
    lost = tools.moment_context("3:23", player="H04")
    assert tools.context_at(1, 203.0, "H04") == lost
    assert lost["team_just_lost_ball"] and lost["possession"] == "away"
    calm = tools.moment_context(12.0, 1, "H04")  # 12 min in, 1–0, home on the ball since 4:20
    assert [r["code"] for r in calm["non_fatigue_reasons"]] == ["team_in_possession"]
    assert calm["ball_in_play"] and not calm["team_just_lost_ball"]
    _numbers_have_units(ctx)


def test_claim_and_verify_tools(tools):
    assert tools.claim("33")["status"] == "blocked" and "error" in tools.claim("99")
    assert tools.verify("He is tired.")["ok"] is False
    ctx = tools.moment_context("50:30", 2, team="home")
    v = tools.verify("A typical professional would likely be in the red after this.", "fan", ctx)
    assert not v["ok"] and v["findings"][0]["claim"] == "13"


def test_agents_never_read_truth():
    """Static check, as test_engine_never_imports_truth: no agents module uses the truth reader
    or models, or names truth.json in code."""
    banned = {"read_truth", "MatchTruth", "PlayerTruth", "TruthSeries", "TrueParams", "TRUTH"}
    for path in AGENTS.glob("*.py"):
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.ImportFrom | ast.Import):
                names = {a.name for a in node.names}
                assert not names & banned, (path.name, names & banned)
            used = getattr(node, "id", None) or getattr(node, "attr", None)
            assert used not in banned, (path.name, used)
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                assert not node.value.strip().endswith("truth.json"), path.name


def test_tools_never_open_truth_json(folder, monkeypatch):
    opened: list[str] = []
    real_open = io.open

    def spy(file, *args, **kwargs):
        opened.append(str(file))
        return real_open(file, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", spy)
    monkeypatch.setattr(io, "open", spy)
    t = MatchTools(folder)
    for kind in MOMENT_KINDS:
        t.find_moments(kind)
    t.match_summary()
    monkeypatch.undo()
    names = {Path(p).name for p in opened}
    assert "truth.json" not in names
    assert {"signals.json", "tracking.jsonl", "events.jsonl", "metadata.json"} <= names


def test_mcp_server_serves_the_seven_read_only_tools(folder):
    pytest.importorskip("mcp")
    from runningbattery.agents.mcp_server import build

    server = build(folder)

    async def run():
        listed = await server.list_tools()
        result = await server.call_tool("claim", {"claim_id": "11"})
        return listed, result

    listed, result = asyncio.run(run())
    assert {t.name for t in listed} == {"match_summary", "player_signals", "find_moments",
                                        "team_running", "moment_context", "claim",
                                        "verify"}  # fmt: skip
    assert all(t.annotations.readOnlyHint for t in listed)
    assert "typical professional" in json.dumps(result[1] if isinstance(result, tuple) else
                                                result.structuredContent)  # fmt: skip


def test_offline_feed_is_verified_and_timestamped(folder):
    feed = asyncio.run(feed_mod.build(folder, offline=True))
    assert feed["synthetic"] and feed["moments"] and feed["agents"]["tactical"] == "offline"
    keys = {"t", "period", "clock", "video_s", "player", "kind", "sentence", "claim", "sources",
            "mode", "verdict", "shown", "verifier"}  # fmt: skip
    assert {e["mode"] for e in feed["entries"]} == {"fan", "analyst"}
    for e in feed["entries"]:
        assert keys <= e.keys()
        if e["shown"]:
            assert verify(e["sentence"], e["mode"]).ok, e["sentence"]
            assert e["sources"]
    assert any(e["player"] is None and e["kind"] == "tug_of_war" for e in feed["entries"])
    times = [e["video_s"] for e in feed["entries"]]
    assert times == sorted(times)
    for mode in feed_mod.MODES:  # a team moment says how the two teams compare (decision 25)
        team = [e["sentence"] for e in feed["entries"]
                if e["kind"] == "tug_of_war" and e["mode"] == mode and e["shown"]]  # fmt: skip
        assert any(re.search(feed_mod.MUST_SAY["ran harder"], x) for x in team), team
    assert "favourite" not in feed  # no favourite player (decision 42)
    # The substitute who out-ran his team-mates is a key moment (ensure_key).
    assert any(m["moment_id"].startswith("fresh_legs:H12") for m in feed["moments"])


def test_exposed_on_turnover_after_the_so_far_bar(folder, monkeypatch):
    import runningbattery.agents.tools as tools_mod

    monkeypatch.setattr(tools_mod, "SO_FAR_MIN_S", 0)
    exposed = MatchTools(folder).find_moments("exposed_on_turnover", player="H04")["moments"]
    assert exposed and exposed[0]["t"] == 200.5 and exposed[0]["facts"]["counter_xg"]["value"]


def test_general_sentences_at_most_twice_per_mode():
    def e(v, claim, mode="fan"):
        return {"video_s": v, "claim": claim, "mode": mode, "shown": True, "verdict": "pass"}

    entries = [e(30, "1"), e(10, "1"), e(20, "1"), e(40, "1", "analyst"), e(50, "11"),
               e(60, "11"), e(70, "11"), e(80, "fact"), e(90, "6")]  # fmt: skip
    feed_mod.cap_general(entries)
    assert [x["shown"] for x in entries] == [False] + [True] * 8  # the third use, in match order
    assert entries[0]["verdict"] == "repeat" and feed_mod.MAX_GENERAL == 2
    assert feed_mod.unlabel("fact: he had 0 touches.") == "He had 0 touches."
    assert feed_mod.unlabel("Factually level.") == "Factually level."
    # Decision 31: a bare claim id ("11: He has done…"), never a clock.
    assert feed_mod.unlabel("9a: Albion did more.") == "Albion did more."
    assert feed_mod.unlabel("60:00–75:00 — level.") == "60:00–75:00 — level."
    rep = [
        {
            "moment_id": "m",
            "mode": "fan",
            "shown": True,
            "verdict": "fallback",
            "sentence": "Since coming on, he has done 15.5 m/min, 64% more than his team-mates.",
        },
        {
            "moment_id": "m",
            "mode": "fan",
            "shown": True,
            "verdict": "pass",
            "sentence": "That's 64% more than his team-mates over the same minutes.",
        },
    ]
    feed_mod.cap_repeated_numbers(rep)
    assert [x["shown"] for x in rep] == [True, False] and rep[1]["verdict"] == "repeat"


def test_moments_say_what_they_are_for():
    """Decision 31: a substitute against his team-mates, a player caught on the break with the
    typical-pro line (any player since decision 42), and a team moment's comparison; decision
    39: a second wind against his match average; the others need nothing."""
    bat = {"typical_pro_battery_now": {"value": 0.83, "unit": "share"}}
    exposed = {"kind": "exposed_on_turnover", "player": {"id": "H04"}, "facts": bat}
    assert feed_mod.needs(exposed) == feed_mod.EXPOSED_SAYS
    assert feed_mod.needs(exposed | {"facts": {}}) is None
    sub = {"kind": "fresh_legs", "player": {"id": "H16"},
           "facts": {"vs_teammates": {"value": 49, "unit": "%"}}}  # fmt: skip
    assert feed_mod.needs(sub) == feed_mod.FRESH_LEGS_SAYS
    team = {"kind": "tug_of_war", "facts": {"pattern": "ran harder"}}
    assert feed_mod.needs(team) == feed_mod.MUST_SAY["ran harder"]
    assert feed_mod.needs({"kind": "second_wind", "facts": {}}) == feed_mod.SECOND_WIND_SAYS
    assert feed_mod._pro(exposed)[1].startswith("That running would leave a typical professional")


def test_a_counter_that_ended_in_a_goal_says_so():
    """Decision 39: caught on the break by a counter that scored, a line says the goal ("his own
    goal" does not count); without the goal nothing is added."""
    player = {"id": "H04", "name": "Marco Tarvsall", "shirt": 3, "team": "home",
              "team_name": "Westerlyn Albion"}  # fmt: skip
    b = {"kind": "exposed_on_turnover", "player": player, "facts": {"counter_goal": True},
         "claims": [], "non_fatigue_reasons": [], "context": {}, "moment_id": "m",
         "_when": {"t": 1.0, "period": 1, "clock": "0:01", "video_s": 1.0}}  # fmt: skip
    line = {"shown": True, "sentence": "He ran back towards his own goal."}
    out = asyncio.run(feed_mod.must_say(b, "fan", [line], None))
    assert [e["sentence"] for e in out[1:]] == [
        "The counter-attack after Westerlyn Albion lost the ball ended in a goal."
    ]
    said = {"shown": True, "sentence": "This is the fourth time, and that counter ended in a goal."}
    assert asyncio.run(feed_mod.must_say(b, "fan", [said], None)) == [said]
    b["facts"]["counter_goal"] = False
    assert asyncio.run(feed_mod.must_say(b, "fan", [line], None)) == [line]


def test_highlights_are_measured_ranked_and_verified(folder):
    """Decision 28: H04's two 60-s runs at 7.5 m/s top the longest-run and top-speed lists;
    every kept event was among the top 3 players when it happened; captions pass the rules."""
    from runningbattery.agents import highlights as hl

    m = MatchTools(folder).m
    out = hl.highlights(m)
    assert out and {h["kind"] for h in out} <= set(hl.KINDS)
    longest = [h for h in out if h["kind"] == "longest_run"]
    assert longest[0]["player"]["id"] == "H04" and longest[0]["facts"]["metres"]["value"] > 300
    # The 1-Hz Butterworth filter overshoots a step from standing to 7.5 m/s by about 0.5 m/s.
    assert abs(longest[0]["facts"]["top_speed"]["value"] - 7.5) < 0.6
    for h in out:
        assert verify(h["caption"], "fan", {"facts": h["facts"]}).ok, h["caption"]
        assert h["start_video_s"] <= h["video_s"] <= h["end_video_s"] and h["sources"]
        _numbers_have_units(h["facts"])
    # Ranking: a later, smaller event of the same player is not kept.
    ev = [{"kind": "top_speed", "player": p, "period": 1, "t": t, "value": v}
          for p, t, v in [("A", 1, 8.0), ("B", 2, 7.0), ("C", 3, 6.0), ("D", 4, 5.0),
                          ("A", 5, 7.5), ("D", 6, 9.0)]]  # fmt: skip
    kept = [(e["player"], e["t"]) for e in hl.ranked(ev)]
    assert kept == [("A", 1), ("B", 2), ("C", 3), ("D", 6)]


def test_most_ground_and_recovery_runs(folder, monkeypatch):
    """Decision 29: most ground covered at the final whistle (whole-match players only, the
    top 3), and a recovery run (back towards his own goal within 10 s of his team losing it)."""
    from runningbattery.agents import highlights as hl

    m = MatchTools(folder).m
    lost = hl.losses(m, "home")
    assert lost[1].tolist() == [200] and lost[2].size == 0
    assert hl.losses(m, "away")[1].tolist() == [260]
    out = hl.highlights(m)
    ground = [h for h in out if h["kind"] == "most_ground"]
    assert len(ground) == hl.TOP and ground[0]["player"]["id"] == "H04"
    assert all(h["player"]["id"] not in ("H11", "H12") for h in ground)  # subbed off / on
    assert abs(ground[0]["facts"]["metres"]["value"] - 900) < 60  # two 60-s runs at 7.5 m/s
    assert "km over the match" in ground[0]["caption"]
    # No run in the constructed match starts just after a loss; make H04's second run one.
    poss = list(m.possession[1])
    poss[695:700] = ["home"] * 4 + ["away"]
    monkeypatch.setitem(m.possession, 1, poss)
    monkeypatch.setattr(hl, "where", lambda *a: "back towards his own goal")
    monkeypatch.setattr(hl, "zone", lambda m, pid, per, k: ("his own half", -k / 20.0))
    rec = [e for e in hl.candidates(m) if e["kind"] == "recovery_run"]
    assert [e["player"] for e in rec] == ["H04"]
    f = rec[0]["facts"]
    assert f["seconds_after_loss"]["value"] <= hl.RECOVERY_WITHIN_S and f["metres"]["value"] > 300
    text = hl.caption(m, rec[0])
    assert "back towards his own goal" in text and verify(text, "fan", {"facts": f}).ok


def test_general_claims_with_only_measured_numbers_are_facts():
    """Decision 29: a line the Narrator tagged with a general claim (6, 9b) but whose numbers
    all come from the moment's facts is a measured fact."""
    b = {"kind": "fresh_legs", "facts": {"sub_hsr_per_min": {"value": 12.2, "unit": "m/min"}},
         "claims": [{"id": "6", "wording": "Fresh legs: substitutes typically do 15–25% more "
                     "high-intensity running per minute than players who started."}]}  # fmt: skip
    assert feed_mod.as_fact(b, "6", "Theo Galdcott has done 12.2 m/min since coming on.") == "fact"
    assert feed_mod.as_fact(b, "6", b["claims"][0]["wording"]) == "6"
    assert feed_mod.as_fact(b, "11", "That would leave a typical professional at 12%.") == "11"


def test_running_split_by_situation(folder, tools):
    """Decision 30: where each team's high-speed running happened, from possession and the
    ball's position only. Home lose the ball at 200 s and win it back at 260 s (period 1); A04
    runs 300–360 s without the ball (ball on the centre spot, so in the middle third)."""
    from runningbattery.agents.tools import SITUATIONS, TRANSITION_S
    from runningbattery.export import team_situations

    m = tools.m
    sit = m.situations[1]
    assert set(sit["home"][200:210]) == {"after_losing"} and sit["home"][210] == "off_ball_deep"
    assert set(sit["away"][200:210]) == {"after_winning"} and sit["away"][210] == "on_ball"
    assert set(sit["away"][260:270]) == {"after_losing"} and sit["home"][265] == "after_winning"
    assert sit["home"][0] == "on_ball"  # the half's first holder is no change of possession
    assert set(m.situations[2]["home"][300:360]) == {""}  # the stoppage: ball out of play
    r = m.team_situations(1, 0, DURATION[0])
    assert sum(x["in_play_s"] for x in r["home"].values()) == DURATION[0]
    assert r["home"]["after_losing"]["in_play_s"] == TRANSITION_S
    assert r["home"]["off_ball_high"]["in_play_s"] == 0  # the ball never left the middle third
    away = r["away"]["off_ball_deep"]["hsr"]
    assert away / sum(x["hsr"] for x in r["away"].values()) > 0.95 and abs(away - 360) < 40
    split = tools.team_running()["situations"]
    assert set(split["home"]) == set(SITUATIONS)
    assert abs(sum(x["share_of_hsr"]["value"] for x in split["away"].values()) - 100) <= 3
    assert split["away"]["off_ball_deep"]["hsr_per_min"]["value"] > 0
    _numbers_have_units(split)
    tug = tools.find_moments("tug_of_war")["moments"][0]
    assert "4" in tug["claims"] and "team_hsr_share_after_ball_changed_hands" in tug["facts"]
    blocks = team_situations(m)
    assert [b["from"] for b in blocks] == ["0:00", "45:00"]
    assert blocks[0]["away"]["off_ball_deep"][0] == round(away)
    assert sum(s for _, s in blocks[0]["home"].values()) == DURATION[0]


def test_team_moment_lines_never_blame_fatigue():
    """Decision 30: on a team moment, claim 4's "tired legs" would be about the team (35)."""
    wording = (
        "Losing the ball forces the hardest running of the game. This is where tired legs get "
    )
    wording += "exposed."
    ctx = {"facts": {}, "team_moment": True}
    v = verify(wording, "fan", ctx, "4")
    assert not v.ok and "35" in {f.claim for f in v.findings}
    assert verify(wording, "fan", {"facts": {}}, "4").ok  # a player's moment: fine
    assert verify("Losing the ball forces the hardest running of the game.", "fan", ctx, "4").ok


def test_purpose_rules_against_the_truth(folder, monkeypatch):
    """validate/purposes.py: our runs take the purpose of the truth run they overlap, and the
    recovery-run rule needs his team without the ball, 10 m back and the wrong side of it."""
    from types import SimpleNamespace

    from runningbattery.agents.tools import MatchData
    from runningbattery.schema import RunPurpose
    from runningbattery.validate import purposes as P

    m = MatchData(folder)
    xy = m.xy[1].copy()
    a04 = m.col["A04"]
    xy[302, a04], xy[360, a04] = (-20.0, 0.0), (8.0, 0.0)  # his run: 302–359 s; 28 m back
    monkeypatch.setitem(m.xy, 1, xy)
    monkeypatch.setattr(P, "MatchData", lambda folder: m)
    run = lambda pid, a, b, why: SimpleNamespace(  # noqa: E731
        player_id=pid, period=1, t_start=a, t_end=b, purpose=RunPurpose(why), executed=True
    )
    truth = [run("A04", 300.5, 359.0, "recovery_run"), run("H04", 60.0, 120.0, "run_with_ball"),
             run("A08", 10.0, 12.0, "close_down")]  # fmt: skip
    monkeypatch.setattr(P, "read_truth", lambda folder: SimpleNamespace(runs=truth))
    runs, totals = P.labelled_runs(folder)
    a = [r for r in runs if r["purpose"] == "recovery_run"]
    assert len(a) == 1 and "recovery_ju" in a[0]["labels"] and "press_ju" not in a[0]["labels"]
    assert "recovery_highlight" not in a[0]["labels"]  # 40 s after his team lost the ball
    assert all(not r["labels"] for r in runs if r["purpose"] == "run_with_ball")
    rep = P.score(runs, totals)
    assert rep["recovery_ju"]["precision"] == 1.0 and rep["recovery_ju"]["recall"] == 1.0
    assert rep["press_ju"]["recall"] == 0.0  # A08's run is not in our speed: missed


def test_key_moments_join_the_pick_and_wordings_keep_their_claim():
    """Decision 42 (no favourite player): the best-ranked moment of each key kind joins the pick
    (the next best when it clashes and the agent left that kind out), and (decision 39) the best
    turnover that ended in a goal;
    a register wording tagged "fact" is that claim."""

    def mo(i, kind, pid, v, score):
        return {"id": i, "kind": kind, "player": {"id": pid}, "video_s": v, "score": score}

    found = {m["id"]: m for m in [mo("a", "exposed_on_turnover", "H04", 100.0, 1.0),
                                  mo("b", "exposed_on_turnover", "A05", 900.0, 3.0),
                                  mo("c", "fresh_legs", "H16", 2000.0, 1.0)]}  # fmt: skip
    assert feed_mod.ensure_key(["a"], found) == ["a", "b", "c"]  # the best-ranked one too
    assert feed_mod.ensure_key(["c"], found) == ["b", "c"]
    found["b"]["video_s"] = 1990.0  # the best clashes with the fresh legs: the next best, only
    assert feed_mod.ensure_key(["c"], found) == ["a", "c"]  # when there is none of its kind
    assert feed_mod.ensure_key(["a", "c"], found) == ["a", "c"]
    found["b"]["video_s"] = 900.0
    # Decision 39: and the turnover that ended in a goal, though it ranks lower.
    found["g"] = mo("g", "exposed_on_turnover", "H04", 1500.0, 0.5) | {
        "facts": {"counter_goal": True}
    }
    assert feed_mod.ensure_key(["b", "c"], found) == ["b", "g", "c"]
    w9b = (
        "Without the ball, Premier League players typically cover about 10% more ground per "
        "minute than when they have it."
    )
    b = {"kind": "tug_of_war", "facts": {}, "claims": [{"id": "9b", "wording": w9b}]}
    assert feed_mod.as_fact(b, "fact", w9b) == "9b"
    assert (
        feed_mod.as_fact(b, "fact", "Albion did 433 m per minute after losing the ball.") == "fact"
    )


def test_moment_clips_show_the_moment(tools):
    """A moment measured over minutes gets the part of the match that shows it, and a moment
    whose player does nothing above 5.5 m/s gets no clip, except a quiet one (decision 38)."""
    from runningbattery.export import CLIP_AFTER, CLIP_BEFORE, moment_clips, player_runs

    m = tools.m
    runs = {pid: player_runs(m, pid) for pid in m.series}
    pid = max(runs, key=lambda p: len(runs[p]))
    a, b, _ = max(runs[pid], key=lambda r: r[2])
    at = a + 60.0
    best = max((r for r in runs[pid] if at - 120.0 <= r[0] <= at), key=lambda r: r[2])
    s = m.series[pid]
    on = [m.video_s(int(p), float(t)) for p, t in zip(s.period, s.t, strict=True)]
    quiet = next(
        v for v in on[60:]
        if not any(r[0] < v + 4 + CLIP_AFTER and r[1] > v - 8 - CLIP_BEFORE for r in runs[pid])
    )  # fmt: skip
    feed = {"moments": [
        {"moment_id": f"second_wind:{pid}:1:1", "kind": "second_wind", "video_s": at},
        {"moment_id": f"flat_out:{pid}:1:2", "kind": "flat_out", "video_s": quiet},
        {"moment_id": f"not_tired_tactical:{pid}:1:3", "kind": "not_tired_tactical",
         "video_s": quiet},
        {"moment_id": f"exposed_on_turnover:{pid}:1:200", "kind": "exposed_on_turnover",
         "period": 1, "t": 200.5, "video_s": 200.5},
        {"moment_id": "tug_of_war:home:1:4", "kind": "tug_of_war", "video_s": 100.0},
    ]}  # fmt: skip
    clips = moment_clips(m, feed)
    assert clips[f"second_wind:{pid}:1:1"] == [round(best[0], 1), round(best[1], 1)]
    assert clips[f"flat_out:{pid}:1:2"] is None
    assert f"not_tired_tactical:{pid}:1:3" not in clips
    assert clips[f"exposed_on_turnover:{pid}:1:200"] == [200.5, 206.5]
    assert "tug_of_war:home:1:4" not in clips


def test_caught_on_the_break_needs_the_counter_near_him_or_a_shot(tools):
    """Decision 38: a clip showed him 34 m from a counter that went elsewhere."""
    from runningbattery.agents.tools import COUNTER_MAX_S, COUNTER_MIN_S, COUNTER_NEAR_M

    for x in tools.find_moments("exposed_on_turnover", limit=100)["moments"]:
        f = x["facts"]
        near = f["ball_nearest_him_in_counter"]["value"]
        assert near <= COUNTER_NEAR_M or f["counter_xg"]["value"] > 0 or f["counter_goal"]
        assert COUNTER_MIN_S <= f["counter_seconds"]["value"] <= COUNTER_MAX_S


def test_possessives_of_names_ending_in_s():
    """Decision 41: the feed showed "Ravensholt Harriers's"."""
    assert feed_mod.possessive("Ravensholt Harriers") == "Ravensholt Harriers'"
    assert feed_mod.possessive("Westerlyn Albion") == "Westerlyn Albion's"
    b = {"kind": "red_zone", "player": {"name": "Sam Jones"},
         "facts": {"hardest_minutes_count": 1, "peak_1min_hsr": 70}}  # fmt: skip
    lines = [x for x in feed_mod.template(b, "fan") if x]
    assert lines[0][1].startswith("Sam Jones' hardest minutes so far")
    assert 'never "Harriers\'s"' in feed_mod.NARRATOR


def test_so_far_claims_need_ten_minutes_on_the_pitch(folder, monkeypatch):
    """Decision 41: "his hardest minutes so far" at 1:47 is true of almost any running. H04's
    first hard minute (60–120 s) is no moment; his second (700–760 s) is, and only its brief
    offers "the lowest point of his match so far"."""
    import runningbattery.agents.tools as T

    tools = MatchTools(folder)
    red = tools.find_moments("red_zone", 10, player="H04")["moments"]
    assert red and all(m["period"] == 2 or m["t"] >= T.SO_FAR_MIN_S for m in red)
    monkeypatch.setattr(T, "SO_FAR_MIN_S", 0)
    early = MatchTools(folder).find_moments("red_zone", 10, player="H04")["moments"]
    first = min(early, key=lambda m: (m["period"], m["t"]))
    assert first["period"] == 1 and first["t"] < 130.0
    assert "lowest_typical_pro_battery_so_far" not in feed_mod.brief(tools, first)["facts"]
    later = next(m for m in red if m["period"] == 1)
    facts = feed_mod.brief(tools, later)["facts"]
    assert "lowest_typical_pro_battery_so_far" in facts
    # Unrounded (decision 41: 0.620 against an earlier 0.618 both read as 0.62).
    s = tools.m.series["H04"]
    battery = s.cols["battery"][: s.index(later["period"], later["t"]) + 1]
    assert facts["at_lowest_point_so_far"] == bool(battery[-1] <= battery.min())
    line = "This is the lowest point of his match so far, by our estimate."
    v = verify(line, "fan", {"facts": facts | {"at_lowest_point_so_far": False}})
    assert not v.ok and "19c" in {f.claim for f in v.findings}


def test_nearest_to_the_ball_reads_every_frame(folder):
    """Decision 41: "as close as 2 m" from the 1-Hz samples was 1.2 m in the full tracking."""
    m = MatchTools(folder).m
    times = np.round(np.arange(0.0, 3.01, 0.1), 1)
    xy = np.full((len(times), len(m.col), 2), np.nan)
    xy[:, 0] = np.stack([times * 4.0 - 6.0, np.full(len(times), 1.2)], axis=1)  # passes at 1.5 s
    m._full = {1: (times, xy, np.zeros((len(times), 2)))}
    assert m.nearest_ball(1, 0.0, 3.0, 0) == pytest.approx(1.2)
    assert min(np.hypot(*(xy[times == s, 0][0])) for s in (1.0, 2.0)) > 2.0  # each second


def test_red_zone_clip_shows_the_running_of_the_minute():
    """Decision 41: the clip of his hardest minutes shows the runs that made them, the cluster
    within RED_ZONE_CLIP_MAX_S holding most of the minute's metres, not the 8 s before it; since
    decision 42 that is the whole minute (the overlay fast-forwards between his runs)."""
    from runningbattery.export import red_zone_window

    runs = [(1953.0, 1956.0, 23.0), (1991.0, 1994.0, 20.0), (2006.0, 2007.0, 6.0),
            (2011.0, 2013.0, 13.0), (2100.0, 2104.0, 40.0)]  # fmt: skip
    assert red_zone_window(runs, 2012.0) == [1953.0, 2010.0]  # all of the minute's 62 m
    assert red_zone_window(runs, 1960.0) == [1953.0, 1958.0]  # played on to the moment
    assert red_zone_window(runs, 2090.0) is None  # nothing above 5.5 m/s in that minute


def test_a_key_moment_replaces_another_view_of_the_same_action():
    """Decision 41: the agent picked a team-mate's view of a turnover (both caught on the same
    counter), and the key one could not join within a minute of it; since decision 42 the
    best-ranked turnover that ended in a goal is the key one."""

    def mo(i, kind, pid, v, score, goal=False):
        return {"id": i, "kind": kind, "player": {"id": pid}, "video_s": v, "score": score,
                "facts": {"counter_goal": goal}}  # fmt: skip

    found = {m["id"]: m for m in [mo("h03", "exposed_on_turnover", "H03", 535.0, 2.0),
                                  mo("h04", "exposed_on_turnover", "H04", 554.0, 1.0, True),
                                  mo("red", "red_zone", "H05", 600.0, 2.0),
                                  mo("sub", "fresh_legs", "H16", 2000.0, 1.0)]}  # fmt: skip
    # Another kind that near stays, and so the goal's turnover waits for another chance.
    assert feed_mod.ensure_key(["h03", "red", "sub"], found) == ["h03", "red", "sub"]
    found["red"]["video_s"] = 700.0
    assert feed_mod.ensure_key(["h03", "red", "sub"], found) == ["h04", "red", "sub"]


def test_one_hardest_minutes_moment_per_episode():
    """Decision 43: two clips of one spell both said "for the sixth time" (2 of 7 real matches'
    feeds, 2 of 30 synthetic); the agent's pick and the offline one keep the best-ranked."""

    def mo(i, pid, v, score, n):
        return {"id": i, "kind": "red_zone", "player": {"id": pid}, "video_s": v, "score": score,
                "rank": -score, "facts": {"hardest_minutes_count": {"value": n}}}  # fmt: skip

    found = {m["id"]: m for m in [mo("a", "H09", 1000.0, 1.0, 6), mo("b", "H09", 1300.0, 2.0, 6),
                                  mo("c", "H09", 2000.0, 1.5, 7),
                                  mo("d", "A04", 1100.0, 0.5, 6)]}  # fmt: skip
    assert feed_mod.ensure_key(["a", "c", "d"], found) == ["d", "b", "c"]
    assert feed_mod.pick_offline(found) == ["d", "b", "c"]  # a is b's episode: d takes its place


def test_a_closed_gap_says_the_blocks_own_comparison():
    """Decision 43: the natural feed's one fan line on a closed gap gave the earlier 18% and not
    the block's 3%, and the template said "level" (G10 blocks it at 3%), so nothing was added."""
    b = {"kind": "tug_of_war", "player": None,
         "team": {"id": "away", "name": "Ravensholt Harriers"},
         "opponent": {"name": "Westerlyn Town"},
         "facts": {"pattern": "gap closed", "block": "30:00–45:00",
                   "vs_opponent": {"value": 3}, "earlier_gap_vs_opponent": {"value": 18},
                   "team_hsr_per_in_play_min": {"value": 150},
                   "opponent_hsr_per_in_play_min": {"value": 146}}}  # fmt: skip
    need = feed_mod.needs(b)
    earlier_only = "The gap has closed after Ravensholt Harriers did up to 18% more earlier."
    assert not re.search(need, earlier_only, re.I)
    for mode in feed_mod.MODES:
        line = feed_mod.template(b, mode)[0][1]
        assert re.search(need, line, re.I) and "level" not in line, line
    b["facts"]["vs_opponent"]["value"] = 0
    assert re.search(feed_mod.needs(b), feed_mod.template(b, "fan")[0][1], re.I)


def test_exported_signals_read_the_lines_second_in_both_halves(folder, tools, tmp_path):
    """Decision 44: the first half ends mid-second, and one count from ``start`` read the second
    half a second late (55% on screen against the line's "about 54%"); each half now has its own
    first second (``halves``), and the overlay's lookup (``signalPos`` in data.ts) at a moment's
    video_s finds the row the line read."""
    import math

    from runningbattery.export import export

    export(folder, tmp_path)
    signals = json.loads((tmp_path / "signals.json").read_text())
    m = tools.m
    for pid, s in m.series.items():
        hs = signals[pid]["halves"]
        for i in range(0, len(s.t), 37):
            v = m.video_s(int(s.period[i]), float(s.t[i]) + 0.5)
            t0, k0 = [h for h in hs if h[0] <= v][-1]
            assert k0 + math.floor(v - t0) == s.index(int(s.period[i]), float(s.t[i]) + 0.5)
    # The committed story match's first half ends mid-second: a second-half time reads the second
    # half's own count, where one count from ``start`` would be a second behind.
    data = Path(__file__).resolve().parents[1] / "app" / "public" / "data" / "story"
    periods = json.loads((data / "match.json").read_text())["periods"]
    second = next(p["video_start"] for p in periods if p["period"] == 2)
    assert second % 1
    for s in json.loads((data / "signals.json").read_text()).values():
        if len(s["halves"]) == 2:
            t0, k0 = s["halves"][1]
            assert t0 == second and k0 == math.floor(second - s["start"]) + 1
