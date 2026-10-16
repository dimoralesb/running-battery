"""Run the estimator on one match: positions in, ``MatchSignals`` out (PLAN §3).

The estimator sees ``tracking.jsonl``, ``events.jsonl`` and ``metadata.json`` only (``io.Match``),
never ``truth.json``. Club test values in the metadata are used in club mode only; broadcast
mode (the product) drops them before anything else runs.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Literal

import numpy as np

from secondwind.engine import params as P
from secondwind.engine.battery import BatteryResult, prior_draws, run
from secondwind.engine.preprocess import Tracks, tracks
from secondwind.engine.signals import Seconds, per_second, red_zone, spells, tired
from secondwind.io import Match
from secondwind.schema import (
    Capacity,
    EngineSettings,
    MatchSignals,
    PlayerSignals,
    Range,
    SignalSeries,
    TiredSpell,
)

Mode = Literal["broadcast", "club"]
Update = Literal["draws", "correction"]


@dataclass(frozen=True)
class Estimate:
    """Everything the estimator computed, as arrays, plus the settings used."""

    settings: EngineSettings
    tracks: Tracks
    battery: BatteryResult
    seconds: Seconds


def broadcast_view(match: Match) -> Match:
    """The match as a broadcaster has it: club test values removed."""
    teams = [
        team.model_copy(
            update={"players": [p.model_copy(update={"test_values": None}) for p in team.players]}
        )
        for team in match.metadata.teams
    ]
    return replace(match, metadata=match.metadata.model_copy(update={"teams": teams}))


def capacities(
    match: Match, ids: list[str], mode: Mode, update: Update, n_draws: int, prior: P.Prior
) -> tuple[np.ndarray, np.ndarray]:
    """(players, draws) starting CS and D′ for each player."""
    if mode == "club":
        tests = {p.id: p.test_values for team in match.metadata.teams for p in team.players}
        # Goalkeepers have no test values: the shared prior's mean.
        cs = [tests[i].cs if tests[i] else prior.cs_mean for i in ids]
        dp = [tests[i].d_prime if tests[i] else prior.d_prime_mean for i in ids]
        return np.array(cs)[:, None], np.array(dp)[:, None]
    if update == "correction":
        n = len(ids)
        return np.full((n, 1), prior.cs_mean), np.full((n, 1), prior.d_prime_mean)
    draws = np.stack([prior_draws(i, n_draws, prior=prior) for i in ids])
    return draws[..., 0], draws[..., 1]


def compute(
    match: Match,
    mode: Mode = "broadcast",
    update: Update = "draws",
    k: float = P.K,
    n_draws: int = P.N_DRAWS,
    penalty_width: float = P.PENALTY_WIDTH,
    prior: str = P.DEFAULT_PRIOR,
) -> Estimate:
    if mode == "broadcast":
        match = broadcast_view(match)
    else:
        update = "correction"
    settings = EngineSettings(
        mode=mode,
        update=update,
        prior=prior,
        k=k,
        n_draws=n_draws if update == "draws" else 1,
        penalty_width=penalty_width,
        low_battery=P.LOW_BATTERY,
        peak_share=P.PEAK_SHARE,
        peak_floor=P.PEAK_FLOOR,
        hi_speed=P.HI_SPEED,
    )
    tr = tracks(match)
    cs, dp = capacities(match, tr.ids, mode, update, n_draws, P.PRIORS[prior])
    bat = run(tr.speed, tr.period, tr.whole_second, cs, dp, k, penalty_width)
    return Estimate(settings, tr, bat, per_second(tr, bat))


def _r(x: np.ndarray, digits: int = 3) -> list[float]:
    return (np.round(x, digits) + 0.0).tolist()


def to_signals(match: Match, est: Estimate) -> MatchSignals:
    s, st = est.seconds, est.settings
    hot, post = red_zone(s, st.peak_share, st.peak_floor)
    flag = tired(s, st.low_battery)
    red = np.logical_or.reduce(list(hot.values()))
    info = {p.id: (team.id, p) for team in match.metadata.teams for p in team.players}
    events = [e for e in match.events if e.player_id is not None]
    kinds = set(P.DEFENSIVE_EVENTS) | {"ball_loss"}
    players, tired_spells = [], []
    for j, pid in enumerate(est.tracks.ids):
        m = s.on[:, j]
        team_id, p = info[pid]
        ref = {
            w: np.maximum(
                np.maximum.accumulate(np.where(s.full[w][:, j] & m, s.hsr[w][:, j], 0.0)),
                st.peak_floor * pub * w / 60.0,
            )
            for w, pub in zip(P.HSR_WINDOWS_S, P.PUBLISHED_PEAK_M_PER_MIN, strict=True)
        }
        band = s.battery_lo is not None and s.battery_hi is not None
        series = SignalSeries(
            period=s.period[m].tolist(),
            t=s.t[m].astype(float).tolist(),
            speed=_r(s.speed[m, j], 2),
            battery=_r(s.battery[m, j]),
            battery_lo=_r(s.battery_lo[m, j]) if band else None,
            battery_hi=_r(s.battery_hi[m, j]) if band else None,
            power=_r(s.power[m, j], 2),
            power_1min=_r(s.power_avg[60][m, j], 2),
            power_5min=_r(s.power_avg[300][m, j], 2),
            energy=_r(s.energy[m, j]),
            hsr_1min=_r(s.hsr[60][m, j], 1),
            hsr_2min=_r(s.hsr[120][m, j], 1),
            hsr_5min=_r(s.hsr[300][m, j], 1),
            hsr_1min_vs_peak=_r(s.hsr[60][m, j] / ref[60][m]),
            hsr_2min_vs_peak=_r(s.hsr[120][m, j] / ref[120][m]),
            hsr_5min_vs_peak=_r(s.hsr[300][m, j] / ref[300][m]),
            in_play_1min=_r(np.clip(s.in_play[60][m, j], 0, 1)),
            in_play_5min=_r(np.clip(s.in_play[300][m, j], 0, 1)),
            red_zone=red[m, j].tolist(),
            post_peak=post[m, j].tolist(),
            tired=flag[m, j].tolist(),
        )
        c, d = est.battery.cs[j], est.battery.d_prime[j]
        players.append(
            PlayerSignals(
                player_id=pid,
                team_id=team_id,
                position=p.position,
                starter=p.starter,
                capacity=Capacity(
                    cs=Range(value=round(c[1], 3), lo=round(c[0], 3), hi=round(c[2], 3)),
                    d_prime=Range(value=round(d[1], 1), lo=round(d[0], 1), hi=round(d[2], 1)),
                ),
                series=series,
            )
        )
        mine = [e for e in events if e.player_id == pid and e.type.value in kinds]
        for per in np.unique(s.period):
            rows = np.flatnonzero(s.period == per)
            for a, b in spells(flag[rows, j]):
                ra, rb = rows[a], rows[b]
                t0, t1 = float(s.t[ra]), float(s.t[rb])
                tired_spells.append(
                    TiredSpell(
                        player_id=pid,
                        period=int(per),
                        t_start=t0,
                        t_end=t1,
                        post_peak=bool(post[ra : rb + 1, j].any()),
                        battery_min=round(float(s.battery[ra : rb + 1, j].min()), 3),
                        event_ids=[e.id for e in mine if e.period == per and t0 - 1.0 < e.t <= t1],
                    )
                )
    tired_spells.sort(key=lambda x: (x.period, x.t_start, x.player_id))
    return MatchSignals(
        match_id=match.metadata.match_id,
        engine=st,
        players=players,
        tired_spells=tired_spells,
    )


def estimate(match: Match, **kw) -> MatchSignals:
    """Signals for one match (keyword arguments as in :func:`compute`)."""
    return to_signals(match, compute(match, **kw))
