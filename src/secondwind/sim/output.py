"""Run one seeded match and turn the engine's arrays and event log into the four files.

Fatigue is on by default; ``fatigue=False`` gives the no-fatigue control (PLAN §2.5): the same
seed, teams, physiology settings, tempo and work rates, with every player fresh all match. The
tempo is drawn from its own generator, so with ``tempo=False`` as well (and the fatigue-off
calibration, ``params.PRE_FATIGUE``) the match is the one the generator made before fatigue and
tempo existed (81f023d), file for file, apart from ``schema_version``; that mode also makes no
substitutions (81f023d had none).

Substitutions (``subs``, on by default) are planned from their own generator before kick-off, so
the no-fatigue control makes the same ones. A substitute takes over the engine slot of the player
replaced; the files use player ids throughout (``Spell``: who was in which slot when).

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
    Substitution,
    TrackingFrame,
    TruthSeries,
)
from secondwind.sim import params as P
from secondwind.sim.match import MatchEngine, PeriodFrames
from secondwind.sim.physiology import Physiology
from secondwind.sim.rosters import SimPlayer, SimTeam, make_teams, plan_substitutions
from secondwind.sim.runs import hi_runs

PERIOD_2_CLOCK = 2700.0  # schema: period 2 starts at 45:00 on the match clock
CLEAN_COPY = Path("debug") / "tracking_clean.npz"  # inside the match folder; debugging only


@dataclass(frozen=True)
class Observed:
    """What the tracking system reports for one period."""

    pos: np.ndarray  # (n, 22, 2) noise-free positions plus noise, inside the schema limits
    seen: np.ndarray  # (n, 22) bool; False is a dropout (the player is left out of the frame)


@dataclass(frozen=True)
class Spell:
    """A player's time on the pitch in one engine slot, from ``on`` up to (not including)
    ``off``, each (period, s since the period's kick-off); ``off`` None: to the final whistle."""

    player: SimPlayer
    slot: int
    on: tuple[int, float] = (1, 0.0)
    off: tuple[int, float] | None = None

    def holds(self, period: int, t: float) -> bool:
        return self.on <= (period, t) and (self.off is None or (period, t) < self.off)


def spells(teams: list[SimTeam], sub_log: list, bench: dict[str, SimPlayer]) -> list[Spell]:
    """Every player's spell: starters in slot order, then substitutes in the order they came
    on. ``sub_log`` is ``MatchEngine.sub_log``."""
    out = [Spell(p, 11 * k + j) for k, team in enumerate(teams) for j, p in enumerate(team.players)]
    for period, t, slot, off_id, on_id in sub_log:
        k = next(n for n, s in enumerate(out) if s.player.id == off_id)
        out[k] = Spell(out[k].player, slot, out[k].on, (period, t))
        out.append(Spell(bench[on_id], slot, (period, t)))
    return out


def owner(all_spells: list[Spell], slot: int, period: int, t: float) -> Spell:
    """The spell of the player in ``slot`` at that moment."""
    return next(s for s in all_spells if s.slot == slot and s.holds(period, t))


@dataclass(frozen=True)
class SimMatch:
    metadata: MatchMetadata
    periods: list[PeriodFrames]  # noise-free
    observed: list[Observed]
    events: list[Event]
    truth: MatchTruth
    physiology: Physiology | None = None  # in memory only, for the fatigue checks
    spells: list[Spell] | None = None  # in memory only: who was in which slot when


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
    subs: bool = True,
    vary: bool = False,
) -> SimMatch:
    """One match. Club test values go into the metadata only if ``club_tests`` is set; the
    match itself is the same either way. Noise is drawn after the match, so ``noise_sigma``
    changes only the tracking positions. ``tempo``: True draws the shared tempo, a number fixes
    it (a story control), False leaves it out. ``subs``: substitutions (never with fatigue and
    tempo both off). ``vary`` (the validation batch): this match draws its own fatigue effect
    sizes and position noise (``noise_sigma`` is then ignored), and players come from a wider
    prior (``draw_variation``); all of it goes into truth.json ``settings``. The tempo, the
    fatigue skips, the substitutions and the variation have their own generators (spawned from
    the seed), so they never shift the match flow's draws."""
    rng = np.random.default_rng(seed)
    tempo_rng, fatigue_rng, subs_rng, vary_rng = (
        np.random.default_rng(s) for s in np.random.SeedSequence(seed).spawn(4)
    )
    effects, prior = draw_variation(vary_rng) if vary else ({}, None)
    if vary:
        noise_sigma = effects.pop("noise_sigma_m")
    teams = make_teams(rng, prior)
    lengths = period_lengths(rng)
    first_kick = int(rng.integers(2))
    drawn = draw_tempo(tempo_rng)
    match_tempo = None if tempo is False else (drawn if tempo is True else float(tempo))
    players = [p.params for team in teams for p in team.players]
    body = Physiology(players, fatigue_rng, effects) if fatigue else None
    legacy = body is None and match_tempo is None  # params.PRE_FATIGUE calibration
    plans = plan_substitutions(subs_rng, teams, prior) if subs and not legacy else []
    engine = MatchEngine(rng, teams, body, match_tempo, pre_fatigue=legacy, subs=plans)
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
    bench = {plan.player.id: plan.player for plan in plans}
    played = spells(teams, engine.sub_log, bench)
    came_on = [s.player for s in played if not s.player.starter]
    metadata = MatchMetadata(
        match_id=match_id,
        generator=Generator(version=__version__, seed=seed),
        frame_rate_hz=P.FRAME_RATE_HZ,
        periods=infos,
        teams=[
            team.info(club_tests, tuple(p for p in came_on if p.id[0] == team.side[0].upper()))
            for team in teams
        ],
        substitutions=[
            Substitution(
                period=period,
                t=t,
                team_id=teams[slot // 11].id,
                player_out=off_id,
                player_in=on_id,
            )
            for period, t, slot, off_id, on_id in engine.sub_log
        ],
    )
    settings: dict[str, float] = noise_settings(noise_sigma)
    if match_tempo is not None:
        settings["tempo"] = match_tempo
    if vary:
        settings |= {"varied": True} | prior_settings(prior)
    if body is None:
        truth = neutral_truth(match_id, played, periods, settings)
    else:
        truth = fatigue_truth(match_id, played, periods, body, settings | body.settings())
    return SimMatch(metadata, periods, observed, to_events(engine), truth, body, played)


def to_events(engine: MatchEngine) -> list[Event]:
    team_ids = [team.id for team in engine.teams]
    rows = sorted(engine.events, key=lambda e: (e["period"], e["t"], e["seq"]))
    events = []
    for n, e in enumerate(rows):
        clock = e["t"] + (PERIOD_2_CLOCK if e["period"] == 2 else 0.0)
        events.append(
            Event(
                id=n,
                period=e["period"],
                t=e["t"],
                clock=round(clock, 1),
                type=e["type"],
                subtype=None if e.get("subtype") is None else str(e["subtype"]),
                player_id=e["player_id"],
                team_id=None if e["team"] is None else team_ids[e["team"]],
                related_player_id=e.get("related_player_id"),
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
    played: list[Spell], periods: list[PeriodFrames], body: Physiology | None = None
) -> list[RunTruth]:
    """Every high-intensity run with its purpose (``runs.py``), and, with fatigue on, the hard
    runs tired players skipped (``executed=False``; one per situation, only those forecast to
    have been high-intensity runs, ``Physiology.skipped_runs``; ``t_end`` is the planned end,
    cut at the end of the period). Ordered by period, start time and player."""
    rows = []
    for pf in periods:
        length = (len(pf.alive) - 1) / P.FRAME_RATE_HZ
        found = [
            (r.t_start, r.player, r.t_end, r.purpose, True) for r in hi_runs(pf.pos, pf.purpose)
        ]
        if body is not None:
            found += [
                (s.t_start, s.player, min(s.t_end, length), s.purpose, False)
                for s in body.skipped_runs()
                if s.period == pf.period
            ]
            found.sort(key=lambda r: (r[0], r[1], not r[4]))
        for t_start, player, t_end, purpose, executed in found:
            rows.append(
                RunTruth(
                    run_id=len(rows),
                    player_id=owner(played, player, pf.period, t_start).player.id,
                    period=pf.period,
                    t_start=round(t_start, 1),
                    t_end=round(max(t_end, t_start), 1),
                    purpose=purpose,
                    executed=executed,
                )
            )
    return rows


def draw_variation(rng: np.random.Generator) -> tuple[dict[str, float], dict]:
    """This match's validation spread (PLAN §2.6, point 3): effect sizes and position noise,
    each uniform in its ``params.VARY`` range, and the wider player prior
    (``params.VARY_PLAYERS``)."""
    effects = {k: round(float(rng.uniform(*r)), 4) for k, r in P.VARY.items()}
    return effects, dict(P.VARY_PLAYERS)


def prior_settings(prior: dict) -> dict[str, float]:
    """The player prior for ``settings``, ranges as ``_lo`` and ``_hi``."""
    out = {}
    for k, v in prior.items():
        name = f"prior_{k.removesuffix('_range')}"
        if isinstance(v, tuple):
            out[f"{name}_lo"], out[f"{name}_hi"] = v
        else:
            out[name] = v
    return out


def noise_settings(sigma: float) -> dict[str, float]:
    """The position-noise assumptions of a match, for ``truth.json``'s ``settings``."""
    return {
        "noise_sigma_m": sigma,
        "dropouts_per_min": P.DROPOUTS_PER_MIN,
        "dropout_s_min": P.DROPOUT_S[0],
        "dropout_s_max": P.DROPOUT_S[1],
    }


def _by_team(played: list[Spell]) -> list[Spell]:
    """Home players (starters, then substitutes), then away: the metadata order."""
    return sorted(played, key=lambda s: (s.slot // 11, not s.player.starter))


def neutral_truth(
    match_id: str,
    played: list[Spell],
    periods: list[PeriodFrames],
    settings: dict[str, float] | None = None,
) -> MatchTruth:
    """Truth with fatigue off (the no-fatigue control): full pools and tank, all multipliers 1,
    for each player's seconds on the pitch. The runs and their purposes are real."""
    period, t = [], []
    for pf in periods:
        seconds = (len(pf.alive) - 1) // round(P.FRAME_RATE_HZ) + 1
        period += [pf.period] * seconds
        t += [float(s) for s in range(seconds)]
    players = []
    for spell in _by_team(played):
        keep = [spell.holds(h, s) for h, s in zip(period, t, strict=True)]
        n = sum(keep)
        series = TruthSeries(
            period=[h for h, k in zip(period, keep, strict=True) if k],
            t=[s for s, k in zip(t, keep, strict=True) if k],
            fast_pool=[1.0] * n,
            slow_pool=[1.0] * n,
            tank=[1.0] * n,
            speed_mult=[1.0] * n,
            accel_mult=[1.0] * n,
            run_choice_mult=[1.0] * n,
            tired=[False] * n,
        )
        players.append(
            PlayerTruth(player_id=spell.player.id, params=spell.player.params, series=series)
        )
    return MatchTruth(
        match_id=match_id,
        fatigue_enabled=False,
        settings=settings or {},
        players=players,
        runs=run_truth(played, periods),
    )


def fatigue_truth(
    match_id: str,
    played: list[Spell],
    periods: list[PeriodFrames],
    body: Physiology,
    settings: dict[str, float],
) -> MatchTruth:
    """Truth with fatigue on: each player's pools, tank, multipliers and tired moments, one
    value per second on the pitch (``Physiology.series``), and the runs made and skipped."""
    players = []
    for spell in _by_team(played):
        whole = spell.on == (1, 0.0) and spell.off is None
        keep = (
            None
            if whole
            else np.array(
                [spell.holds(h, t) for h, t in zip(body.periods, body.times, strict=True)]
            )
        )
        series = body.series(spell.slot, keep)
        players.append(
            PlayerTruth(player_id=spell.player.id, params=spell.player.params, series=series)
        )
    return MatchTruth(
        match_id=match_id,
        fatigue_enabled=True,
        settings=settings,
        players=players,
        runs=run_truth(played, periods, body),
    )


def tracking_frames(match: SimMatch) -> Iterator[TrackingFrame]:
    """Frames built without per-row validation (fast); tests validate them on read."""
    ids = [p.id for team in match.metadata.teams for p in team.players if p.starter]
    team_ids = [team.id for team in match.metadata.teams]
    frame = 0
    for pf, obs in zip(match.periods, match.observed, strict=True):
        changes: dict[int, list[tuple[int, str]]] = {}
        for k, slot, pid in pf.subs:
            changes.setdefault(k, []).append((slot, pid))
        clock0 = PERIOD_2_CLOCK if pf.period == 2 else 0.0
        pos = (np.round(obs.pos, 2) + 0.0).tolist()
        seen = obs.seen.tolist()
        ball = (np.round(pf.ball, 2) + 0.0).tolist()
        for k in range(len(pf.alive)):
            for slot, pid in changes.get(k, ()):
                ids[slot] = pid
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
    subs: bool = True,
    vary: bool = False,
) -> SimMatch:
    """Simulate one match and write its four files to ``folder`` (match id: folder name)."""
    match = simulate(
        seed, match_id or folder.name, club_tests, noise_sigma, fatigue, tempo, subs, vary
    )
    write(match, folder, clean_copy)
    return match
