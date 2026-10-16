"""Run one seeded match and turn the engine's arrays and event log into the four files.

Fatigue is on by default; ``fatigue=False`` gives the no-fatigue control (PLAN §2.5): the same
seed, teams, physiology settings, tempo and work rates, with every player fresh all match. The
tempo is drawn from its own generator, so with ``tempo=False`` as well (and the fatigue-off
calibration, ``params.PRE_FATIGUE``) the match is the one the generator made before fatigue and
tempo existed (81f023d), file for file.

``tracking.jsonl`` carries position noise and dropouts (``observe``); the engine's noise-free
positions can be saved next to the four files for debugging (``CLEAN_COPY``). That copy is never
part of the match data: ``read_match`` ignores it and the estimator must not read it.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from secondwind import __version__
from secondwind.io import write_match
from secondwind.schema import (
    X_LIMIT,
    Y_LIMIT,
    Ball,
    BallStatus,
    Event,
    Generator,
    MatchMetadata,
    MatchTruth,
    PeriodInfo,
    PlayerPosition,
    PlayerTruth,
    Point,
    RunTruth,
    Score,
    TrackingFrame,
    TruthSeries,
)
from secondwind.sim import params as P
from secondwind.sim.match import MatchEngine, PeriodFrames
from secondwind.sim.physiology import Physiology
from secondwind.sim.rosters import SimTeam, make_teams
from secondwind.sim.runs import hi_runs

PERIOD_2_CLOCK = 2700.0  # schema: period 2 starts at 45:00 on the match clock
CLEAN_COPY = Path("debug") / "tracking_clean.npz"  # inside the match folder; debugging only


@dataclass(frozen=True)
class Observed:
    """What the tracking system reports for one period."""

    pos: np.ndarray  # (n, 22, 2) noise-free positions plus noise, inside the schema limits
    seen: np.ndarray  # (n, 22) bool; False is a dropout (the player is left out of the frame)


@dataclass(frozen=True)
class SimMatch:
    metadata: MatchMetadata
    periods: list[PeriodFrames]  # noise-free
    observed: list[Observed]
    events: list[Event]
    truth: MatchTruth
    physiology: Physiology | None = None  # in memory only, for the fatigue checks


def period_lengths(rng: np.random.Generator) -> list[int]:
    """Frames in each half. Total 99.5 ± 2.9 min [Allen2025, Table 2]; split is our assumption."""
    lo = P.MATCH_MINUTES_MEAN - P.MATCH_MINUTES_CLIP_SD * P.MATCH_MINUTES_SD
    hi = P.MATCH_MINUTES_MEAN + P.MATCH_MINUTES_CLIP_SD * P.MATCH_MINUTES_SD
    total_s = 60.0 * float(np.clip(rng.normal(P.MATCH_MINUTES_MEAN, P.MATCH_MINUTES_SD), lo, hi))
    added_s = total_s - 2 * PERIOD_2_CLOCK
    first_s = PERIOD_2_CLOCK + rng.uniform(*P.FIRST_HALF_ADDED_SHARE) * added_s
    return [round(first_s * P.FRAME_RATE_HZ), round((total_s - first_s) * P.FRAME_RATE_HZ)]


def observe(
    rng: np.random.Generator, periods: list[PeriodFrames], sigma: float = P.NOISE_SIGMA
) -> list[Observed]:
    """Add Gaussian position noise (σ per axis) and dropouts (synthesis §3.1).

    The draws do not depend on ``sigma``, so changing it rescales the same noise pattern.
    """
    lim = np.array([X_LIMIT, Y_LIMIT])
    out = []
    for pf in periods:
        n = len(pf.alive)
        pos = np.clip(pf.pos + sigma * rng.standard_normal(pf.pos.shape), -lim, lim)
        seen = np.ones((n, 22), dtype=bool)
        minutes = n / P.FRAME_RATE_HZ / 60.0
        for j, count in enumerate(rng.poisson(P.DROPOUTS_PER_MIN * minutes, 22)):
            for _ in range(count):
                start = int(rng.integers(n))
                frames = round(rng.uniform(*P.DROPOUT_S) * P.FRAME_RATE_HZ)
                seen[start : start + frames, j] = False
        out.append(Observed(pos, seen))
    return out


def draw_tempo(rng: np.random.Generator) -> float:
    """One shared tempo per match: N(1, TEMPO_SD), clipped at ±TEMPO_CLIP_SD SD."""
    lo, hi = 1.0 - P.TEMPO_CLIP_SD * P.TEMPO_SD, 1.0 + P.TEMPO_CLIP_SD * P.TEMPO_SD
    return round(float(np.clip(rng.normal(1.0, P.TEMPO_SD), lo, hi)), 4)


def simulate(
    seed: int,
    match_id: str,
    club_tests: bool = False,
    noise_sigma: float = P.NOISE_SIGMA,
    fatigue: bool = True,
    tempo: bool | float = True,
) -> SimMatch:
    """One match. Club test values go into the metadata only if ``club_tests`` is set; the
    match itself is the same either way. Noise is drawn after the match, so ``noise_sigma``
    changes only the tracking positions. ``tempo``: True draws the shared tempo, a number fixes
    it (a story control), False leaves it out. The tempo and the fatigue skips have their own
    generators (spawned from the seed), so they never shift the match flow's draws."""
    rng = np.random.default_rng(seed)
    tempo_rng, fatigue_rng = (
        np.random.default_rng(s) for s in np.random.SeedSequence(seed).spawn(2)
    )
    teams = make_teams(rng)
    lengths = period_lengths(rng)
    first_kick = int(rng.integers(2))
    drawn = draw_tempo(tempo_rng)
    match_tempo = None if tempo is False else (drawn if tempo is True else float(tempo))
    players = [p.params for team in teams for p in team.players]
    body = Physiology(players, fatigue_rng) if fatigue else None
    legacy = body is None and match_tempo is None  # params.PRE_FATIGUE calibration
    engine = MatchEngine(rng, teams, body, match_tempo, pre_fatigue=legacy)
    periods = [
        engine.run_period(1, lengths[0], first_kick),
        engine.run_period(2, lengths[1], 1 - first_kick),
    ]
    observed = observe(rng, periods, noise_sigma)
    infos, start = [], 0
    for pf in periods:
        n = len(pf.alive)
        infos.append(
            PeriodInfo(
                period=pf.period,
                start_frame=start,
                end_frame=start + n - 1,
                duration_s=n / P.FRAME_RATE_HZ,
            )
        )
        start += n
    metadata = MatchMetadata(
        match_id=match_id,
        generator=Generator(version=__version__, seed=seed),
        frame_rate_hz=P.FRAME_RATE_HZ,
        periods=infos,
        teams=[team.info(club_tests) for team in teams],
    )
    settings: dict[str, float] = noise_settings(noise_sigma)
    if match_tempo is not None:
        settings["tempo"] = match_tempo
    if body is None:
        truth = neutral_truth(match_id, teams, periods, settings)
    else:
        truth = fatigue_truth(match_id, teams, periods, body, settings | body.settings())
    return SimMatch(metadata, periods, observed, to_events(engine), truth, body)


def to_events(engine: MatchEngine) -> list[Event]:
    ids, team_ids = engine.ids, [team.id for team in engine.teams]
    rows = sorted(engine.events, key=lambda e: (e["period"], e["t"], e["seq"]))
    events = []
    for n, e in enumerate(rows):
        clock = e["t"] + (PERIOD_2_CLOCK if e["period"] == 2 else 0.0)
        related = e.get("related_player_id")
        events.append(
            Event(
                id=n,
                period=e["period"],
                t=e["t"],
                clock=round(clock, 1),
                type=e["type"],
                subtype=None if e.get("subtype") is None else str(e["subtype"]),
                player_id=ids[e["player"]] if e["player"] >= 0 else None,
                team_id=None if e["team"] is None else team_ids[e["team"]],
                related_player_id=None if related is None else ids[related],
                start=Point(x=e["start"][0], y=e["start"][1]) if "start" in e else None,
                end=Point(x=e["end"][0], y=e["end"][1]) if "end" in e else None,
                end_t=e.get("end_t"),
                outcome=e.get("outcome"),
                body_part=e.get("body_part"),
                height=e.get("height"),
                xg=e.get("xg"),
                possession_id=e.get("possession_id"),
                phase=e.get("phase"),
                score=Score(home=e["score"][0], away=e["score"][1]),
            )
        )
    return events


def run_truth(
    teams: list[SimTeam], periods: list[PeriodFrames], body: Physiology | None = None
) -> list[RunTruth]:
    """Every high-intensity run with its purpose (``runs.py``), and, with fatigue on, the hard
    runs tired players skipped (``executed=False``; ``t_end`` is the planned end, cut at the end
    of the period). Ordered by period, start time and player."""
    ids = [p.id for team in teams for p in team.players]
    rows = []
    for pf in periods:
        length = (len(pf.alive) - 1) / P.FRAME_RATE_HZ
        found = [
            (r.t_start, r.player, r.t_end, r.purpose, True) for r in hi_runs(pf.pos, pf.purpose)
        ]
        if body is not None:
            found += [
                (s.t_start, s.player, min(s.t_end, length), s.purpose, False)
                for s in body.skipped
                if s.period == pf.period
            ]
            found.sort(key=lambda r: (r[0], r[1], not r[4]))
        for t_start, player, t_end, purpose, executed in found:
            rows.append(
                RunTruth(
                    run_id=len(rows),
                    player_id=ids[player],
                    period=pf.period,
                    t_start=round(t_start, 1),
                    t_end=round(max(t_end, t_start), 1),
                    purpose=purpose,
                    executed=executed,
                )
            )
    return rows


def noise_settings(sigma: float) -> dict[str, float]:
    """The position-noise assumptions of a match, for ``truth.json``'s ``settings``."""
    return {
        "noise_sigma_m": sigma,
        "dropouts_per_min": P.DROPOUTS_PER_MIN,
        "dropout_s_min": P.DROPOUT_S[0],
        "dropout_s_max": P.DROPOUT_S[1],
    }


def neutral_truth(
    match_id: str,
    teams: list[SimTeam],
    periods: list[PeriodFrames],
    settings: dict[str, float] | None = None,
) -> MatchTruth:
    """Truth with fatigue off (the no-fatigue control): full pools and tank, all multipliers 1.
    The runs and their purposes are real."""
    period, t = [], []
    for pf in periods:
        seconds = (len(pf.alive) - 1) // round(P.FRAME_RATE_HZ) + 1
        period += [pf.period] * seconds
        t += [float(s) for s in range(seconds)]
    n = len(t)
    series = TruthSeries(
        period=period,
        t=t,
        fast_pool=[1.0] * n,
        slow_pool=[1.0] * n,
        tank=[1.0] * n,
        speed_mult=[1.0] * n,
        accel_mult=[1.0] * n,
        run_choice_mult=[1.0] * n,
        tired=[False] * n,
    )
    players = [
        PlayerTruth(player_id=p.id, params=p.params, series=series)
        for team in teams
        for p in team.players
    ]
    return MatchTruth(
        match_id=match_id,
        fatigue_enabled=False,
        settings=settings or {},
        players=players,
        runs=run_truth(teams, periods),
    )


def fatigue_truth(
    match_id: str,
    teams: list[SimTeam],
    periods: list[PeriodFrames],
    body: Physiology,
    settings: dict[str, float],
) -> MatchTruth:
    """Truth with fatigue on: each player's pools, tank, multipliers and tired moments, one
    value per second (``Physiology.series``), and the runs made and skipped."""
    players = [p for team in teams for p in team.players]
    return MatchTruth(
        match_id=match_id,
        fatigue_enabled=True,
        settings=settings,
        players=[
            PlayerTruth(player_id=p.id, params=p.params, series=body.series(j))
            for j, p in enumerate(players)
        ],
        runs=run_truth(teams, periods, body),
    )


def tracking_frames(match: SimMatch) -> Iterator[TrackingFrame]:
    """Frames built without per-row validation (fast); tests validate them on read."""
    ids = [p.id for team in match.metadata.teams for p in team.players]
    team_ids = [team.id for team in match.metadata.teams]
    frame = 0
    for pf, obs in zip(match.periods, match.observed, strict=True):
        clock0 = PERIOD_2_CLOCK if pf.period == 2 else 0.0
        pos = (np.round(obs.pos, 2) + 0.0).tolist()
        seen = obs.seen.tolist()
        ball = (np.round(pf.ball, 2) + 0.0).tolist()
        for k in range(len(pf.alive)):
            t = round(k / P.FRAME_RATE_HZ, 1)
            holder = int(pf.possession[k])
            yield TrackingFrame.model_construct(
                frame=frame,
                period=pf.period,
                t=t,
                clock=round(clock0 + t, 1),
                ball_status=BallStatus.ALIVE if pf.alive[k] else BallStatus.DEAD,
                possession_team=None if holder < 0 else team_ids[holder],
                ball=Ball.model_construct(x=ball[k][0], y=ball[k][1], z=ball[k][2]),
                players=[
                    PlayerPosition.model_construct(id=pid, x=xy[0], y=xy[1])
                    for pid, xy, ok in zip(ids, pos[k], seen[k], strict=True)
                    if ok
                ],
            )
            frame += 1


def write(match: SimMatch, folder: Path, clean_copy: bool = False) -> None:
    write_match(folder, match.metadata, tracking_frames(match), match.events, match.truth)
    if clean_copy:
        write_clean_copy(match, folder)


def write_clean_copy(match: SimMatch, folder: Path) -> None:
    """Noise-free engine arrays per period (``pos_1``, ``ball_1``, ``alive_1``, ``possession_1``,
    ``purpose_1``, then ``_2``), unrounded. Debugging only."""
    arrays = {}
    for pf in match.periods:
        for name in ("pos", "ball", "alive", "possession", "purpose"):
            arrays[f"{name}_{pf.period}"] = getattr(pf, name)
    path = folder / CLEAN_COPY
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path, **arrays)


def read_clean_copy(folder: Path) -> dict[str, np.ndarray]:
    with np.load(folder / CLEAN_COPY) as data:
        return dict(data)


def generate(
    seed: int,
    folder: Path,
    match_id: str | None = None,
    club_tests: bool = False,
    noise_sigma: float = P.NOISE_SIGMA,
    clean_copy: bool = False,
    fatigue: bool = True,
    tempo: bool | float = True,
) -> SimMatch:
    """Simulate one match and write its four files to ``folder`` (match id: folder name)."""
    match = simulate(seed, match_id or folder.name, club_tests, noise_sigma, fatigue, tempo)
    write(match, folder, clean_copy)
    return match
