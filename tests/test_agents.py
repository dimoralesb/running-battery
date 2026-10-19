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

from secondwind.agents import feed as feed_mod
from secondwind.agents.tools import MOMENT_KINDS, MatchTools, clock_label, parse_time
from secondwind.agents.verifier import verify
from secondwind.engine.estimate import estimate
from secondwind.io import SIGNALS, Match, write_match, write_signals
from secondwind.schema import (
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

AGENTS = Path(__file__).resolve().parents[1] / "src" / "secondwind" / "agents"
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
    assert p["flags"]["intense_spells"]["value"] >= 1
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
    exposed = tools.find_moments("exposed_on_turnover", player="H04")["moments"]
    assert exposed and exposed[0]["t"] == 200.5 and exposed[0]["facts"]["counter_xg"]["value"]
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


def test_flat_out_is_near_his_top_speed_so_far(tools):
    flat = tools.find_moments("flat_out", player="H04")["moments"]
    assert flat and 700.0 <= flat[0]["t"] <= 760.0
    f = flat[0]["facts"]
    assert 90 <= f["share_of_top_speed"]["value"] <= 100 and not f["new_personal_best"]
    assert (
        f["peak_speed_kmh"]["value"] == round(f["peak_speed"]["value"] * 3.6)
        or abs(f["peak_speed_kmh"]["value"] - f["peak_speed"]["value"] * 3.6) < 1
    )
    assert "SilvaH2025" in f["published_match_peak_for_position"]["source"]


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
    from secondwind.agents.mcp_server import build

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
    fav = asyncio.run(feed_mod.build(folder, offline=True, favourite="Sub H"))
    assert fav["favourite"] == "H12"
    # The favourite's replacement counts as his: H11 went off for H12, whose fresh legs show.
    assert feed_mod.related(MatchTools(folder), "H11") == {"H11", "H12"}
    off = asyncio.run(feed_mod.build(folder, offline=True, favourite="H11"))
    assert any(m["moment_id"].startswith("fresh_legs:H12") for m in off["moments"])


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


def test_highlights_are_measured_ranked_and_verified(folder):
    """Decision 28: H04's two 60-s runs at 7.5 m/s top the longest-run and top-speed lists;
    every kept event was among the top 3 players when it happened; captions pass the rules."""
    from secondwind.agents import highlights as hl

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
    from secondwind.agents import highlights as hl

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
