"""Generator: determinism, valid files, the interim realism targets (summary.TARGETS), the motion
model, run purposes, position noise, the fatigue switch and truth.json, and the replay tool.
Physiology and fatigue behaviours on constructed states are in test_fatigue.py."""

import itertools
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from runningbattery.io import EVENTS, METADATA, TRACKING, TRUTH, read_match, read_truth
from runningbattery.schema import X_LIMIT, Y_LIMIT, EventType, MatchMetadata, Position, RunPurpose
from runningbattery.sim import movement, spacing
from runningbattery.sim import params as P
from runningbattery.sim.batch import parse_seeds
from runningbattery.sim.match import MatchEngine, PeriodFrames
from runningbattery.sim.output import CLEAN_COPY, observe, read_clean_copy, simulate
from runningbattery.sim.replay import load_window, write_html
from runningbattery.sim.rosters import make_teams
from runningbattery.sim.runs import speeds
from runningbattery.sim.summary import (
    BALL_IN_PLAY_BAND,
    POSSESSION_BAND,
    TARGETS,
    count_tolerance,
    summarise_match,
)

SEEDS = [1, 2, 3, 4, 5]
MAX_SPEED = 12.0  # m/s (43.2 km/h): nobody is faster between two frames


def _holds(spell, period: int, t: np.ndarray) -> np.ndarray:
    """Frames (times ``t`` of ``period``) when ``spell``'s player was in their slot."""
    on = np.full(len(t), period > spell.on[0]) | ((period == spell.on[0]) & (t >= spell.on[1]))
    if spell.off is not None:
        on &= (period < spell.off[0]) | ((period == spell.off[0]) & (t < spell.off[1]))
    return on


def _per_frame(match, pf, value) -> np.ndarray:
    """(frames, 22): ``value(spell)`` for whoever was in each slot at each frame of ``pf``."""
    t = np.arange(len(pf.alive)) / P.FRAME_RATE_HZ
    out = np.full((len(t), 22), np.nan)
    for spell in match.spells:
        on = _holds(spell, pf.period, t)
        out[on, spell.slot] = value(spell)
    return out


def generate(jobs: list[tuple[int, Path, list[str]]]) -> list[subprocess.Popen]:
    """Start the CLI for several matches at once, as a user would. Wait with ``finish``."""
    return [
        subprocess.Popen(
            [sys.executable, "-m", "runningbattery.sim", "--seed", str(seed), "--out", str(folder)]
            + extra,
            stdout=subprocess.DEVNULL,
        )
        for seed, folder, extra in jobs
    ]


def finish(procs: list[subprocess.Popen]) -> None:
    for proc in procs:
        assert proc.wait(timeout=300) == 0


@pytest.fixture(scope="module")
def generated(tmp_path_factory) -> tuple[dict, object]:
    """The CLI matches, plus seed 1 simulated in this process while they run."""
    root = tmp_path_factory.mktemp("synthetic")
    folders = {seed: root / f"m{seed:04d}" for seed in SEEDS}
    folders["again"] = root / "again" / "m0001"
    folders["club"] = root / "club" / "m0001"
    folders["clean"] = root / "clean" / "m0001"
    folders["off"] = root / "off" / "m0001"
    folders["legacy"] = root / "legacy" / "m0001"
    folders["vary"] = root / "vary" / "m0001"
    jobs = [(seed, folders[seed], []) for seed in SEEDS]
    jobs += [(1, folders["again"], []), (1, folders["club"], ["--club-tests"])]
    jobs += [(1, folders["clean"], ["--clean-copy"]), (1, folders["off"], ["--no-fatigue"])]
    jobs += [(1, folders["legacy"], ["--no-fatigue", "--no-tempo"])]
    jobs += [(1, folders["vary"], ["--vary"])]
    procs = generate(jobs)
    sim1 = simulate(1, "m0001")
    finish(procs)
    return folders, sim1


@pytest.fixture(scope="module")
def folders(generated) -> dict:
    return generated[0]


@pytest.fixture(scope="module")
def sim1(generated):
    return generated[1]


@pytest.fixture(scope="module")
def summaries(folders) -> dict:
    """Read every match with full pydantic validation, keep only the summary."""
    out = {}
    for seed in SEEDS:
        match = read_match(folders[seed])
        out[seed] = (summarise_match(match), _check_match(match))
    return out


def _check_match(match) -> dict:
    """Structural facts gathered while the frames are in memory."""
    meta = match.metadata
    frames = match.frames
    starts = [p.start_frame for p in meta.periods]
    return {
        "frame_numbers_ok": [f.frame for f in frames] == list(range(len(frames))),
        "period_frames_ok": all(
            frames[p.start_frame].period == p.period
            and frames[p.end_frame].period == p.period
            and round((p.end_frame - p.start_frame + 1) / meta.frame_rate_hz, 1) == p.duration_s
            for p in meta.periods
        ),
        "period_2_clock_ok": frames[starts[1]].clock == 2700.0 and frames[starts[1]].t == 0.0,
        "players_per_frame": {len(f.players) for f in frames},
        "dropout_share": 1 - sum(len(f.players) for f in frames) / (22 * len(frames)),
        "events_sorted": all(
            (a.period, a.t) <= (b.period, b.t) for a, b in itertools.pairwise(match.events)
        ),
        "event_ids_ok": [e.id for e in match.events] == list(range(len(match.events))),
        "carries_ok": all(e.end_t is not None for e in match.events if e.type == EventType.CARRY),
        "goals": sum(e.type == EventType.GOAL for e in match.events),
        "truth_seconds": sum((p.end_frame - p.start_frame) // 10 + 1 for p in meta.periods),
        "final_score": match.events[-1].score,
        "no_test_values": all(p.test_values is None for team in meta.teams for p in team.players),
        "subs": len(meta.substitutions),
        "on_pitch": [{p.id for p in f.players} for f in frames[:: 10 * 60]],  # once a minute
        "slot_of": meta.slot_of(),
    }


def test_same_seed_gives_identical_files(folders):
    for name in (TRACKING, EVENTS, METADATA, TRUTH):
        assert (folders[1] / name).read_bytes() == (folders["again"] / name).read_bytes(), name


def test_different_seeds_differ(folders):
    assert (folders[1] / EVENTS).read_bytes() != (folders[2] / EVENTS).read_bytes()


def test_files_validate(folders, summaries):
    for seed in SEEDS:
        truth = read_truth(folders[seed])
        checks = summaries[seed][1]
        assert truth.fatigue_enabled is True
        # 3–5 substitutes per team; a late one may not happen if no stoppage comes in time.
        assert 4 <= checks["subs"] <= 10 and len(truth.players) == 22 + checks["subs"]
        seconds = {}  # a slot's players together cover the whole match, second by second
        for p in truth.players:
            slot = checks["slot_of"][p.player_id]
            seconds[slot] = seconds.get(slot, 0) + len(p.series.t)
        assert set(seconds.values()) == {checks["truth_seconds"]}
        assert all(len(ids) <= 22 for ids in checks["on_pitch"])
        assert truth.runs
        assert truth.settings["noise_sigma_m"] == P.NOISE_SIGMA
        assert truth.settings["tired_below"] == P.TIRED_BELOW
        assert abs(truth.settings["tempo"] - 1) <= P.TEMPO_CLIP_SD * P.TEMPO_SD + 1e-9
        series = truth.players[0].series  # the home goalkeeper plays the whole match
        assert len(series.t) == checks["truth_seconds"]
        assert checks["frame_numbers_ok"] and checks["period_frames_ok"]
        assert checks["period_2_clock_ok"]
        # Dropouts leave a player out of a frame now and then (params.DROPOUTS_PER_MIN).
        assert max(checks["players_per_frame"]) == 22
        assert min(checks["players_per_frame"]) >= 18
        assert 0.0 < checks["dropout_share"] < 0.02
        assert checks["events_sorted"] and checks["event_ids_ok"] and checks["carries_ok"]
        assert checks["no_test_values"]  # broadcast data by default
        score = checks["final_score"]
        assert score.home + score.away == checks["goals"]


def test_match_length(summaries):
    lo = P.MATCH_MINUTES_MEAN - 3 * P.MATCH_MINUTES_SD
    hi = P.MATCH_MINUTES_MEAN + 3 * P.MATCH_MINUTES_SD
    minutes = [summaries[s][0].match_minutes for s in SEEDS]
    assert all(lo <= m <= hi for m in minutes), minutes
    assert abs(np.mean(minutes) - P.MATCH_MINUTES_MEAN) <= P.MATCH_MINUTES_SD


def test_ball_in_play_and_possession(summaries):
    bip = np.mean([summaries[s][0].ball_in_play_pct for s in SEEDS])
    assert BALL_IN_PLAY_BAND[0] <= bip <= BALL_IN_PLAY_BAND[1], bip
    lo, hi = POSSESSION_BAND
    for team in ("home", "away"):
        share = np.mean([summaries[s][0].possession_pct[team] for s in SEEDS])
        assert lo <= share <= hi, (team, share)
    for s in SEEDS:  # also every single match
        assert all(lo <= v <= hi for v in summaries[s][0].possession_pct.values())


@pytest.mark.parametrize(
    "key", ["passes", "shots", "duels", "fouls", "throw_ins", "corners", "transitions", "offsides"]
)
def test_event_counts_near_targets(summaries, key):
    mean = np.mean([summaries[s][0].counts[key] for s in SEEDS])
    target = TARGETS[key][0]
    tolerance = count_tolerance(target, len(SEEDS))
    assert abs(mean - target) <= tolerance * target, (key, mean, target)


def test_club_tests_change_only_the_metadata(folders):
    for name in (TRACKING, EVENTS, TRUTH):
        assert (folders[1] / name).read_bytes() == (folders["club"] / name).read_bytes(), name
    meta = MatchMetadata.model_validate_json((folders["club"] / METADATA).read_text())
    truth = {p.player_id: p.params for p in read_truth(folders["club"]).players}
    for team in meta.teams:
        for p in team.players:
            if p.position == Position.GK:
                assert p.test_values is None
                continue
            for name, sd in P.TEST_ERROR_SD.items():
                ratio = getattr(p.test_values, name) / getattr(truth[p.id], name)
                assert abs(ratio - 1) <= 3 * sd + 0.01, (p.id, name, ratio)


def test_nobody_faster_than_12_m_per_s(summaries):
    """From the noisy tracking after the summary's 1 Hz filter."""
    fastest = max(summaries[s][0].max_step_speed for s in SEEDS)
    assert fastest < MAX_SPEED, fastest


def test_positions_inside_schema_limits(summaries):
    for s in SEEDS:
        e = summaries[s][0].extent
        assert e["player_x"] <= X_LIMIT and e["ball_x"] <= X_LIMIT
        assert e["player_y"] <= Y_LIMIT and e["ball_y"] <= Y_LIMIT
        assert 0.0 <= e["ball_z_min"] and e["ball_z_max"] <= 50.0


def test_summary_cli_runs(folders):
    out = subprocess.run(
        [sys.executable, "-m", "runningbattery.sim.summary", str(folders[1])],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    assert "ball in play" in out and "H01" in out and "A11" in out


# --- Fatigue switch and truth.json ---------------------------------------------------------------


def test_no_fatigue_control(folders):
    """``--no-fatigue``: the same seed, teams, physiology settings, tempo and planned
    substitutions, every player fresh (neutral series, no skipped runs), and the match plays out
    differently (so a substitution may wait for a different stoppage). ``--no-tempo`` as well
    leaves the tempo and the substitutions out (the generator as it was before fatigue and
    tempo, 81f023d; checked file for file on one machine apart from schema_version, since
    matches differ between machines)."""
    on, off, legacy = (read_truth(folders[k]) for k in (1, "off", "legacy"))
    assert off.fatigue_enabled is False and legacy.fatigue_enabled is False
    assert off.settings["tempo"] == on.settings["tempo"] and "tempo" not in legacy.settings
    assert "tank_m" not in off.settings
    for truth in (off, legacy):
        assert all(r.executed for r in truth.runs)
        for p in truth.players:
            assert set(p.series.fast_pool) == {1.0} and set(p.series.run_choice_mult) == {1.0}
            assert not any(p.series.tired)
    meta = {
        k: MatchMetadata.model_validate_json((folders[k] / METADATA).read_text())
        for k in (1, "off", "legacy")
    }
    starters = {k: [p for t in m.teams for p in t.players if p.starter] for k, m in meta.items()}
    assert starters[1] == starters["off"] == starters["legacy"]
    pairs = {k: {s.player_out: s.player_in for s in meta[k].substitutions} for k in (1, "off")}
    shared = pairs[1].keys() & pairs["off"].keys()
    assert len(shared) >= 4 and all(pairs[1][k] == pairs["off"][k] for k in shared)
    assert not meta["legacy"].substitutions and len(legacy.players) == 22
    params = {k: {p.player_id: p.params for p in t.players} for k, t in (("on", on), ("off", off))}
    assert all(params["off"][k] == v for k, v in params["on"].items() if k in params["off"])
    assert (folders[1] / TRACKING).read_bytes() != (folders["off"] / TRACKING).read_bytes()


def test_varied_match_records_its_settings(folders):
    """``--vary``: the match's effect sizes and noise are drawn in their ``params.VARY`` ranges
    and written to ``settings`` with the wider player prior; the label thresholds stay fixed;
    the starters are the same players (same names), with values from the wider prior."""
    plain, varied = read_truth(folders[1]), read_truth(folders["vary"])
    s = varied.settings
    assert s["varied"] is True and "varied" not in plain.settings
    for key, (lo, hi) in P.VARY.items():
        assert lo <= s[key] <= hi, key
    assert s["tired_below"] == P.TIRED_BELOW and s["late_tank_below"] == P.LATE_TANK_BELOW
    assert s["prior_cs_sd"] == P.VARY_PLAYERS["cs_sd"]
    assert (s["prior_d_prime_lo"], s["prior_d_prime_hi"]) == P.VARY_PLAYERS["d_prime_range"]
    meta = {
        k: MatchMetadata.model_validate_json((folders[k] / METADATA).read_text())
        for k in (1, "vary")
    }
    names = {k: [p.name for t in m.teams for p in t.players if p.starter] for k, m in meta.items()}
    assert names[1] == names["vary"]
    assert [p.params for p in plain.players[:22]] != [p.params for p in varied.players[:22]]


def test_truth_series_with_fatigue(sim1):
    """Pools and tank stay fractions; the tank never rises within a half and gets some back at
    half-time; capacity falls by at most CAPACITY_MAX_LOSS; ``tired`` is the pool term below
    TIRED_BELOW (values rounded to 0.001); some players get tired and skip runs."""
    from runningbattery.sim.physiology import below

    tired_any = False
    for p in sim1.truth.players:
        s = p.series
        period = np.array(s.period)
        tank = np.array(s.tank)
        for h in (1, 2):
            assert np.all(np.diff(tank[period == h]) <= 0)
        if (period == 1).any():
            assert tank[period == 2][0] >= tank[period == 1][-1]
        else:  # a substitute comes on fresh
            assert tank[0] == 1.0 and s.fast_pool[0] == 1.0
        assert min(s.speed_mult) >= 1 - P.CAPACITY_MAX_LOSS - 1e-9
        ff = p.params.fast_fraction
        left = ff * np.array(s.fast_pool) + (1 - ff) * np.array(s.slow_pool)
        pools, tired = below(left, P.POOL_FREE, P.POOL_GAIN), np.array(s.tired)
        assert np.all(pools[tired] <= P.TIRED_BELOW + 3e-3)
        assert np.all(pools[~tired] >= P.TIRED_BELOW - 3e-3)
        assert np.all(np.array(s.run_choice_mult)[tired] <= P.TIRED_BELOW + 1e-3)
        tired_any |= tired.any()
    assert tired_any
    skipped = [r for r in sim1.truth.runs if not r.executed]
    assert skipped and all(r.t_end >= r.t_start for r in skipped)
    assert {RunPurpose.RECOVERY_RUN, RunPurpose.COVERING} <= {r.purpose for r in skipped}


def test_capacity_holds_every_frame(sim1):
    """Nobody runs faster than S0 × speed_mult, frame by frame (noise-free positions), whoever
    is in the slot. The multiplier only falls within a half, so the value recorded a second
    earlier bounds it."""
    truth = {p.player_id: p.series for p in sim1.truth.players}
    for pf in sim1.periods:
        v = speeds(pf.pos)
        t = np.arange(len(v)) / P.FRAME_RATE_HZ
        for spell in sim1.spells:
            s = truth[spell.player.id]
            here = np.array(s.period) == pf.period
            if not here.any():
                continue
            seconds, mult = np.array(s.t)[here], np.array(s.speed_mult)[here]
            on = _holds(spell, pf.period, t)
            k = np.clip(np.searchsorted(seconds, t[on], side="right") - 2, 0, len(mult) - 1)
            cap = spell.player.params.s0 * mult[k] + 0.01  # rounding
            assert np.all(v[on, spell.slot] <= cap), spell.player.id


def test_fatigue_checks_on_a_match(sim1):
    """``sim.fatigue_checks`` on a whole match: every pipeline gives numbers, tired players
    skip a larger share of hard runs than fresh ones, and the table prints."""
    from runningbattery.sim import fatigue_checks

    out = fatigue_checks.summarise([fatigue_checks.sim_measure(sim1)])
    assert len(out["leifsson"]) == 9 and all(len(v) == 5 for v in out["leifsson"].values())
    assert np.isfinite(out["end"]["hir_last15_vs_first15"])
    assert out["fang"]["efforts"]["peak"] > 0
    skips = out["skips"]["all"]
    assert skips["tired"] < skips["fresh"] <= 0  # % skipped, as a negative change
    assert 0 < out["tired_pct"] < 100 and 0 < out["late_pct"] < 100
    assert out["subs"]["minutes"] > 0 and np.isfinite(out["subs"]["vs_whole"])
    assert "Leifsson2024" in fatigue_checks.format_table(out, out)


# --- Motion model ---------------------------------------------------------------------------------


def _limits_hold(before: np.ndarray, after: np.ndarray, a0: np.ndarray, s0: np.ndarray) -> None:
    """Speeds one frame apart: never above S0, never gaining faster than a_max(v) [Morin2021],
    never braking harder than BRAKE_MAX."""
    tol = 1e-6
    assert np.all(after <= s0 + tol)
    gain = (after - before) / P.DT
    assert np.all(gain <= movement.a_max(before, a0, s0) + tol), gain.max()
    assert np.all(-gain <= P.BRAKE_MAX + tol), (-gain).max()


def test_motion_model_limits_random_states():
    """Random positions, velocities, targets and wanted speeds, stepped many times."""
    rng = np.random.default_rng(0)
    n = 500
    a0 = rng.uniform(*P.A0_RANGE, n)
    s0 = rng.uniform(*P.S0_RANGE, n)
    pos = rng.uniform(-50, 50, (n, 2))
    direction = rng.normal(size=(n, 2))
    vel = direction / np.hypot(*direction.T)[:, None] * rng.uniform(0, 1, n)[:, None] * s0[:, None]
    for _ in range(200):
        target = (
            rng.uniform(-60, 60, (n, 2)) if rng.random() < 0.2 else pos + rng.normal(0, 20, (n, 2))
        )
        cap = rng.uniform(0.0, 1.2, n) * s0
        before = np.hypot(*vel.T)
        pos, vel = movement.step(pos, vel, target, cap, a0, s0)
        _limits_hold(before, np.hypot(*vel.T), a0, s0)


def test_motion_model_limits_with_push():
    """The push-apart velocity never breaks the limits, and never makes a player faster."""
    rng = np.random.default_rng(1)
    n = 500
    a0 = rng.uniform(*P.A0_RANGE, n)
    s0 = rng.uniform(*P.S0_RANGE, n)
    pos = rng.uniform(-50, 50, (n, 2))
    vel = rng.normal(0, 3, (n, 2))
    for _ in range(200):
        target = pos + rng.normal(0, 10, (n, 2))
        cap = rng.uniform(0.0, 1.2, n) * s0
        push = rng.normal(0, 1, (n, 2)) * rng.uniform(0, P.SEPARATION_MAX, n)[:, None]
        before = np.hypot(*vel.T)
        pos, vel = movement.step(pos, vel, target, cap, a0, s0, push=push)
        _limits_hold(before, np.hypot(*vel.T), a0, s0)
    # A sprinter pushed from behind wants no more speed than before.
    s0 = np.array([9.3])
    args = (np.zeros((1, 2)), np.array([[8.0, 0.0]]), np.array([[100.0, 0.0]]), s0, s0 - 1.9, s0)
    _, plain = movement.step(*args)
    _, pushed = movement.step(*args, push=np.array([[P.SEPARATION_MAX, 0.0]]))
    assert pushed[0, 0] <= plain[0, 0] + 1e-9


def test_push_apart_and_spread_targets():
    team_of = np.array([0, 0, 1, 0])
    # 0 and 1: team-mates on one spot; 2: an opponent 1 m away; 3: far off.
    pos = np.array([[0.0, 0.0], [0.0, 0.0], [1.0, 0.0], [30.0, 0.0]])
    push = movement.push_apart(pos, team_of)
    assert push[0, 0] < 0 < push[1, 0]  # split along x
    assert np.allclose(np.hypot(*push[:2].T), P.SEPARATION_MAX)  # 1.8 m short, capped
    assert np.allclose(push[2:], 0.0)  # 1 m from an opponent is close enough
    # Team-mates 1 m apart: (1.8 − 1) / τ each, straight away from the other.
    near = movement.push_apart(np.array([[0.0, 0.0], [0.0, 1.0]]), np.array([0, 0]))
    gap = P.SEPARATION_TEAM - 1.0
    assert np.allclose(near, [[0.0, -gap / P.SEPARATION_TAU], [0.0, gap / P.SEPARATION_TAU]])
    anchored = np.array([True, False, False, False])
    assert np.allclose(movement.push_apart(pos, team_of, anchored)[0], 0.0)

    spread = movement.spread_targets(pos, team_of)
    assert np.hypot(*(spread[0] - spread[1])) == pytest.approx(P.SEPARATION_TEAM)
    assert np.allclose(spread[2:], pos[2:])  # opponents' targets are left alone
    spread = movement.spread_targets(pos, team_of, anchored)
    assert np.allclose(spread[0], pos[0])  # the anchored player keeps their target
    assert np.hypot(*(spread[1] - pos[0])) == pytest.approx(P.SEPARATION_TEAM)


def test_push_apart_looks_ahead_for_team_mates():
    """Two players 3 m apart running at each other: team-mates step aside, each to their own
    right, before they meet; opponents are judged where they are now (pressing and duels are
    left alone)."""
    pos = np.array([[-1.5, 0.0], [1.5, 0.0]])
    vel = np.array([[1.5, 0.0], [-1.5, 0.0]])
    mates = movement.push_apart(pos, np.array([0, 0]), vel=vel)
    assert mates[0, 1] < 0 < mates[1, 1]
    assert np.allclose(mates[:, 0], 0.0)
    assert np.allclose(movement.push_apart(pos, np.array([0, 0])), 0.0)
    assert np.allclose(movement.push_apart(pos, np.array([0, 1]), vel=vel), 0.0)


def test_push_apart_judges_team_mates_at_closest_approach():
    """Paths that cross half a second from now, 3.06 m apart now and again in 1 s: team-mates
    step aside now (judged at their positions 1 s on, they would not be); opponents are left
    alone."""
    pos = np.array([[-1.5, 0.3], [1.5, -0.3]])
    vel = np.array([[3.0, 0.0], [-3.0, 0.0]])
    mates = movement.push_apart(pos, np.array([0, 0]), vel=vel)
    assert mates[0, 1] > 0 > mates[1, 1]  # sideways, away from where the other will pass
    assert np.allclose(mates[:, 0], 0.0)
    assert np.allclose(movement.push_apart(pos + vel, np.array([0, 0])), 0.0)
    assert np.allclose(movement.push_apart(pos, np.array([0, 1]), vel=vel), 0.0)


def test_dead_ball_separation():
    """While the ball is dead team-mates may stand SEPARATION_DEAD apart, never on one spot."""
    pos = np.array([[0.0, 0.0], [0.0, 1.0]])
    team_of = np.array([0, 0])
    assert np.allclose(movement.push_apart(pos, team_of, team_keep=P.SEPARATION_DEAD), 0.0)
    assert np.allclose(movement.spread_targets(pos, team_of, keep=P.SEPARATION_DEAD), pos)
    same = np.zeros((2, 2))
    spread = movement.spread_targets(same, team_of, keep=P.SEPARATION_DEAD)
    assert np.hypot(*(spread[0] - spread[1])) == pytest.approx(P.SEPARATION_DEAD)
    push = movement.push_apart(same, team_of, team_keep=P.SEPARATION_DEAD)
    assert push[0, 0] < 0 < push[1, 0]


def _engine():
    """An engine a few seconds into a match."""
    rng = np.random.default_rng(0)
    engine = MatchEngine(rng, make_teams(rng))
    engine.run_period(1, 50, 0)
    return engine


def _hold(engine, seconds: float, t0: float = 5.0) -> np.ndarray:
    """Hold the current dead ball (never taken) for ``seconds``; positions of every frame."""
    engine.restart.t = np.inf
    frames = []
    for k in range(round(seconds * P.FRAME_RATE_HZ)):
        t = t0 + k / P.FRAME_RATE_HZ
        engine.follow_ball(t)
        engine.move(t)
        frames.append(engine.pos.copy())
    return np.array(frames)


def _held_restart(kind: str, spot_uv: tuple[float, float], seconds: float = 30.0):
    """An engine a few seconds into a match, then a restart for team 0 at ``spot_uv`` (team 0's
    attacking frame), held for ``seconds`` while everyone moves into place."""
    engine = _engine()
    spot = engine.to_uv(0, np.array(spot_uv))
    engine.schedule_restart(kind, 0, spot, 5.0, spot.copy())
    engine.history = _hold(engine, seconds)
    return engine, spot


def _team_mate_gaps(pos: np.ndarray) -> list[np.ndarray]:
    """Distance from each player to their nearest team-mate, per team."""
    out = []
    for team in (pos[:11], pos[11:]):
        d = np.hypot(*(team[:, None] - team[None]).transpose(2, 0, 1))
        np.fill_diagonal(d, np.inf)
        out.append(d.min(axis=1))
    return out


@pytest.mark.parametrize(
    "kind, spot_uv, keep",
    [
        ("free_kick", (P.HALF_LENGTH - 22.0, 6.0), P.RESTART_DISTANCE),  # in wall range
        ("free_kick", (-10.0, -20.0), P.RESTART_DISTANCE),
        ("corner", (P.HALF_LENGTH, P.HALF_WIDTH), P.RESTART_DISTANCE + P.CORNER_ARC),
        ("throw_in", (5.0, -P.HALF_WIDTH), P.THROW_IN_DISTANCE),
    ],
)
def test_restart_distance_and_taker(kind, spot_uv, keep):
    """Once settled, opponents stand at least 9.15 m from a free kick (Law 13), 9.15 m from the
    corner arc (Laws 1, 17) and 2 m from a throw-in (Law 15) [IFAB2025], give or take the
    approach (0.5 m); the taker about 1 m behind the ball."""
    engine, spot = _held_restart(kind, spot_uv)
    opponents = engine.pos[11:]
    assert np.hypot(*(opponents - spot).T).min() > keep - 0.5
    taker = engine.restart.taker
    assert abs(np.hypot(*(engine.pos[taker] - spot)) - P.TAKER_BEHIND) < 0.3


def test_free_kick_in_range_gets_a_wall():
    """WALL_SIZE[0] defenders side by side, WALL_GAP apart, at the edge of the 9.15 m circle."""
    engine, spot = _held_restart("free_kick", (P.HALF_LENGTH - 24.0, 4.0))
    edge = P.RESTART_DISTANCE + P.RESTART_MARGIN
    wall = engine.pos[engine.roles.wall_members]
    d = np.hypot(*(wall - spot).T)
    assert len(wall) == P.WALL_SIZE[0] and np.all(np.abs(d - edge) < 0.3), d.round(2)
    gaps = np.hypot(*(wall[:, None] - wall[None]).T)
    np.fill_diagonal(gaps, np.inf)
    assert np.allclose(gaps.min(axis=1), P.WALL_GAP, atol=0.15), gaps.min(axis=1)


def test_corner_crowds_the_box():
    """A held corner: the pack (CORNER_PACK) stands side by side, each with a team-mate within
    1 m but never on one spot (SEPARATION_DEAD), and each has a marker within 1.5 m; two
    defenders stand at their zonal spots (CORNER_ZONAL)."""
    engine, _ = _held_restart("corner", (P.HALF_LENGTH, -P.HALF_WIDTH))
    attack, defend = _team_mate_gaps(engine.pos)
    plan = engine.roles.plan
    pack = [i for i, _, holds in plan if holds and i % 11 in P.CORNER_PACK]
    assert len(pack) == len(P.CORNER_PACK)
    assert np.all(attack[pack] < 1.0), attack.round(2)
    assert min(attack.min(), defend.min()) > P.SEPARATION_DEAD - 0.15
    marked = np.hypot(*(engine.pos[pack][:, None] - engine.pos[None, 11:]).transpose(2, 0, 1))
    assert np.all(marked.min(axis=1) < 1.5), marked.min(axis=1)
    zonal = [(i, spot) for i, spot, _ in plan if i - 11 in [s for s, _, _ in P.CORNER_ZONAL]]
    assert len(zonal) == len(P.CORNER_ZONAL)
    assert all(np.hypot(*(engine.pos[i] - spot)) < 1.0 for i, spot in zonal)


def test_free_kick_near_goal_drops_the_defence():
    """A free kick 28 m out (in wall range, not SET_PIECE_U upfield): besides the wall, the
    markers hold a line FREE_KICK_LINE_GAP goal-side of the ball and the attackers stand level
    with it, onside [IFAB2025, Law 11], give or take FREE_KICK_LINE_JITTER (not ruler-straight).
    """
    depth = 28.0
    engine, _ = _held_restart("free_kick", (P.HALF_LENGTH - depth, 3.0))
    line = np.clip(depth - P.FREE_KICK_LINE_GAP, *P.FREE_KICK_LINE)
    u = engine.to_uv(0, engine.pos)[:, 0]  # team 0 attacks towards u = +52.5
    near = P.FREE_KICK_LINE_JITTER + 0.5
    markers = [11 + s for s in P.BOX_MARKERS]
    assert np.all(np.abs(P.HALF_LENGTH - u[markers] - line) < near), (P.HALF_LENGTH - u).round(1)
    forward = [i for i, _, holds in engine.roles.plan if holds]
    assert len(forward) == len(P.BOX_MARKERS)
    assert np.all(np.abs(P.HALF_LENGTH - u[forward] - line - 1.0) < near)
    assert np.std(u[forward]) > 0.2  # staggered
    second_last = np.sort(u[11:])[-2]
    assert u[forward].max() < second_last  # onside


def test_attackers_keep_clear_of_the_wall():
    """Attackers stay at least 1 m from a wall of three or more [IFAB2025, Law 13]: from every
    wall member standing in place (within 0.3 m of its spot), in every frame."""
    engine, _ = _held_restart("free_kick", (P.HALF_LENGTH - 23.0, 1.0))
    wall = engine.roles.wall(True)
    assert len(wall) >= P.WALL_SIZE[0]
    h = engine.history
    in_place = np.stack([np.hypot(*(h[:, i] - spot).T) < 0.3 for i, spot in wall], axis=1)
    assert in_place[-1].all()
    members = [i for i, _ in wall]
    gaps = np.hypot(*(h[:, :11, None] - h[:, None, members]).transpose(3, 0, 1, 2))
    gaps[:, engine.restart.taker] = np.inf
    gaps = np.where(in_place[:, None, :], gaps, np.inf)
    assert gaps.min() >= 1.0, gaps.min()


def test_goal_huddle():
    """After a goal the HUDDLE_N nearest team-mates gather round the scorer (within 1 m, never
    on one spot) and hold for HUDDLE_HOLD_S; then everyone walks back for the kick-off."""
    engine = _engine()
    scorer = 10  # team 0's centre-forward
    engine.goal(5.0, scorer, engine.pos[scorer].copy())
    huddle = engine.restart.huddle
    mates = huddle.mates
    assert len(mates) == P.HUDDLE_N
    frames = _hold(engine, 60.0)
    assert huddle.formed
    close = np.all(
        np.hypot(*(frames[:, mates] - frames[:, None, scorer]).transpose(2, 0, 1)) < 1.0, 1
    )
    held = close[round((huddle.t_end - P.HUDDLE_HOLD_S - 5.0) * P.FRAME_RATE_HZ) :][
        : round(P.HUDDLE_HOLD_S * P.FRAME_RATE_HZ)
    ]
    assert held.mean() > 0.8, held.mean()  # together for most of the hold
    at = frames[round((huddle.t_end - 5.0 - 1.0) * P.FRAME_RATE_HZ)]
    assert _team_mate_gaps(at)[0].min() > P.SEPARATION_DEAD - 0.15
    u = engine.to_uv(0, frames[-1][:11])[:, 0]
    assert np.all(u < 0.0)  # back in their own half, the opponents kick off


def test_free_kicks_keep_distance_over_a_match(sim1):
    """A whole match: the median nearest opponent at a free kick is outside 9.15 m (5.8 m before
    the rule), and nobody is inside the corner circle. Quick free kicks may be taken with
    opponents closer [IFAB2025, Law 13], so single kicks are not judged here."""
    slot = sim1.metadata.slot_of()
    nearest = {"free_kick": [], "corner": []}
    for e in sim1.events:
        if e.type == EventType.PASS and e.subtype in nearest:
            taker = slot[e.player_id]
            pos = sim1.periods[e.period - 1].pos[round(e.t * P.FRAME_RATE_HZ)]
            opponents = pos[11:] if taker < 11 else pos[:11]
            spot = np.array([e.start.x, e.start.y])
            nearest[e.subtype].append(np.hypot(*(opponents - spot).T).min())
    assert np.median(nearest["free_kick"]) > P.RESTART_DISTANCE
    assert min(nearest["corner"]) > P.RESTART_DISTANCE + P.CORNER_ARC


def test_teammates_do_not_stack(sim1):
    """Push-apart on a whole match (noise-free positions, ``sim.spacing``). Bounds: the spread
    over seeds 1–30 plus margin (fatigue on, 2026-10-16; with fatigue off, 2026-10-15, the
    spread was about the same). In play, a team-mate within 1 m in 0.15–0.22% of player-frames
    (0.45% judged 1 s ahead instead of at closest approach, about 0.9% before the push-apart;
    IDSSE 0.20%) and within 0.5 m in 0.01–0.03%. Dead balls crowd on purpose (corner pack,
    walls, goal huddle; SEPARATION_DEAD): within 1 m 1.4–3.4%, but within 0.5 m only
    0.01–0.21%, so nobody stands on a team-mate's spot."""
    s = spacing.sim_measure(sim1)
    assert s["mate_1m_play"] < 0.35, s["mate_1m_play"]
    assert s["mate_0.5m_play"] < 0.06, s["mate_0.5m_play"]
    assert s["ep_mate_max_play"] < 8.0  # in play, nobody stays on a team-mate's spot
    assert 0.8 < s["mate_1m_dead"] < 5.0, s["mate_1m_dead"]
    assert s["mate_0.5m_dead"] < 0.3, s["mate_0.5m_dead"]


def test_motion_model_matches_narizuka_at_full_effort():
    """Straight ahead from rest at full effort the model gives v(t) = S0(1 − e^(−αt)),
    α = A0/S0 [Narizuka2023, Eq. 3–4], up to the explicit-Euler step."""
    a0, s0 = np.array([7.4]), np.array([9.3])
    pos, vel = np.zeros((1, 2)), np.zeros((1, 2))
    target = np.array([[1000.0, 0.0]])
    for _ in range(30):  # 3 s
        pos, vel = movement.step(pos, vel, target, s0, a0, s0)
    expected = s0[0] * (1 - np.exp(-a0[0] / s0[0] * 3.0))
    assert abs(vel[0, 0] - expected) < 0.15, (vel[0, 0], expected)
    assert abs(vel[0, 1]) < 1e-9


def test_match_motion_within_limits(sim1):
    """Every player, every frame of a whole match (noise-free positions), with the values of
    whoever is in the slot."""
    for pf in sim1.periods:
        v = speeds(pf.pos)
        a0 = _per_frame(sim1, pf, lambda s: s.player.params.a0)[1:-1]
        s0 = _per_frame(sim1, pf, lambda s: s.player.params.s0)[1:-1]
        _limits_hold(v[:-1], v[1:], a0, s0)


# --- Run purposes ---------------------------------------------------------------------------------


def test_runs_have_valid_purposes_and_times(folders, sim1):
    seen: set[RunPurpose] = set()
    for seed in SEEDS:
        truth = read_truth(folders[seed])
        meta = MatchMetadata.model_validate_json((folders[seed] / METADATA).read_text())
        length = {
            p.period: (p.end_frame - p.start_frame) / meta.frame_rate_hz for p in meta.periods
        }
        ids = {p.id for team in meta.teams for p in team.players}
        assert [r.run_id for r in truth.runs] == list(range(len(truth.runs)))
        for r in truth.runs:
            assert r.purpose in RunPurpose and r.player_id in ids
            assert 0.0 <= r.t_start and r.t_end <= length[r.period]
            if r.executed:  # a skipped run keeps its planned end (test_truth_series_with_fatigue)
                assert r.t_end - r.t_start >= P.HI_MIN_S - 1e-9
                seen.add(r.purpose)
    # Both phases of play show up: most of Ju2022's classes appear in five matches.
    assert len(seen) >= 9, seen
    assert {RunPurpose.RECOVERY_RUN, RunPurpose.COVERING, RunPurpose.RUN_IN_BEHIND} <= seen


def test_runs_are_high_intensity(sim1):
    """Each run made is above 5.5 m/s for its whole span [Ju2022, p.974], and only those
    spells."""
    slot = sim1.metadata.slot_of()
    v = {pf.period: speeds(pf.pos) for pf in sim1.periods}
    rate = P.FRAME_RATE_HZ
    for r in sim1.truth.runs:
        if not r.executed:
            continue
        a, b = round(r.t_start * rate), round(r.t_end * rate)
        j = slot[r.player_id]
        assert np.all(v[r.period][a:b, j] > P.HI_SPEED)
        assert a == 0 or v[r.period][a - 1, j] <= P.HI_SPEED
        assert b == len(v[r.period]) or v[r.period][b, j] <= P.HI_SPEED


# --- Position noise -------------------------------------------------------------------------------


def test_clean_copy_matches_simulation_and_changes_no_file(folders, sim1):
    for name in (TRACKING, EVENTS, METADATA, TRUTH):
        assert (folders[1] / name).read_bytes() == (folders["clean"] / name).read_bytes(), name
    assert not (folders[1] / CLEAN_COPY).exists()
    clean = read_clean_copy(folders["clean"])
    for pf in sim1.periods:
        for name in ("pos", "ball", "alive", "possession", "purpose"):
            assert np.array_equal(clean[f"{name}_{pf.period}"], getattr(pf, name)), name
    read_match(folders["clean"])  # the extra folder does not get in the way


def test_noise_size_and_dropouts(folders, sim1):
    """tracking.jsonl = noise-free positions + N(0, σ) per axis, rounded to 1 cm."""
    match = read_match(folders[1])
    slot = match.metadata.slot_of()
    clean = np.concatenate([pf.pos for pf in sim1.periods])
    errors, missing = [], 0
    for k, frame in enumerate(match.frames):
        got = {p.id: (p.x, p.y) for p in frame.players}
        missing += 22 - len(got)
        errors += [np.subtract(xy, clean[k, slot[pid]]) for pid, xy in got.items()]
    errors = np.array(errors)
    assert abs(errors.mean()) < 0.005
    assert abs(errors.std() - P.NOISE_SIGMA) < 0.01, errors.std()
    expected = P.DROPOUTS_PER_MIN * np.mean(P.DROPOUT_S) / 60.0  # share of player-frames
    assert 0.5 * expected < missing / clean[..., 0].size < 1.5 * expected


def _period(pos: np.ndarray) -> PeriodFrames:
    """A stand-in period with these noise-free positions (n, 22, 2)."""
    n = len(pos)
    no_purpose = np.full((n, 22), -1, np.int8)
    return PeriodFrames(
        1, pos, np.zeros((n, 3)), np.ones(n, bool), np.zeros(n, np.int8), no_purpose
    )


def test_noise_is_deterministic_and_scales_with_sigma():
    """Same generator state → same noise; sigma only rescales it; dropouts do not change."""
    pos = np.zeros((600, 22, 2))
    pf = _period(pos)
    a = observe(np.random.default_rng(7), [pf], 0.1)[0]
    b = observe(np.random.default_rng(7), [pf], 0.1)[0]
    c = observe(np.random.default_rng(7), [pf], 0.3)[0]
    zero = observe(np.random.default_rng(7), [pf], 0.0)[0]
    assert np.array_equal(a.pos, b.pos) and np.array_equal(a.seen, b.seen)
    assert np.allclose(c.pos, 3 * a.pos) and np.array_equal(a.seen, c.seen)
    assert np.array_equal(zero.pos, pos)


def test_noise_keeps_positions_inside_schema_limits():
    pos = np.tile([[X_LIMIT - 0.01, -Y_LIMIT + 0.01]], (100, 22, 1))
    noisy = observe(np.random.default_rng(1), [_period(pos)], 1.0)[0].pos
    assert np.all(np.abs(noisy[..., 0]) <= X_LIMIT) and np.all(np.abs(noisy[..., 1]) <= Y_LIMIT)


# --- Tools ----------------------------------------------------------------------------------------


def test_batch_seed_parsing():
    assert parse_seeds("1-3,7") == [1, 2, 3, 7]
    assert parse_seeds("5") == [5]


def test_replay_html(folders, tmp_path):
    window = load_window(folders[1], start=600.0, seconds=5.0, purposes=True)
    assert len(window["frames"]) == 50 and window["frames"][0]["clock"] == 600.0
    out = tmp_path / "replay.html"
    write_html(window, out)
    html = out.read_text()
    assert "<canvas" in html and window["teams"][0] in html


def test_replay_stills(folders, tmp_path):
    pytest.importorskip("matplotlib")
    from runningbattery.sim.replay import write_stills

    out = tmp_path / "stills.png"
    write_stills(load_window(folders[1], start=600.0, seconds=4.0), out, 2)
    assert out.stat().st_size > 10_000


def test_story_controls_press_until_the_hour_and_sub_the_exposed_full_back():
    """Story controls (PLAN §2.3; sim.story): the press is on for the pressing team only, until
    press_until_min; the story substitution takes the exposed full-back's slot, like for like,
    and keeps the number of substitutions."""
    from runningbattery.sim.rosters import make_teams, plan_substitutions
    from runningbattery.sim.story import STORIES, story_subs

    story = STORIES["press-fade"]
    assert story.pressing(0, 59 * 60.0) and not story.pressing(0, 60 * 60.0)
    assert not story.pressing(1, 10 * 60.0)
    rng = np.random.default_rng(3)
    teams = make_teams(rng)
    plans = plan_substitutions(rng, teams)
    new = story_subs(plans, teams, story)
    assert len(new) == len(plans)
    mine = [p for p in new if p.slot == story.exposed_slot]
    assert len(mine) == 1 and mine[0].clock_s == story.sub_minute * 60.0
    off = teams[0].players[story.exposed_slot]
    assert mine[0].player.position == off.position == "FB" and mine[0].player.slot == off.slot
    assert len({p.slot for p in new}) == len(new)  # a slot is substituted once
    assert story.settings()["name"] == "press-fade"
