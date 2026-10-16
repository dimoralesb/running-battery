"""Two fictional teams: names, line-ups, hidden true values and club test values.

Club and player names are built from invented place names and syllables. They are meant to
sound plausible, not to match any real club or player (none were checked against real squads).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from secondwind.schema import ClubTestValues, PlayerInfo, Position, TeamInfo, TrueParams
from secondwind.sim import params as P

PLACES = [
    "Fellhaven",
    "Brackenmoor",
    "Corrowdale",
    "Westerlyn",
    "Saltmere",
    "Ravensholt",
    "Kelderby",
    "Aldermoor",
    "Thistlewick",
    "Glenmarsh",
]
SUFFIXES = ["Athletic", "Rovers", "Wanderers", "Town", "Albion", "Harriers"]
FIRST_NAMES = [
    "Adam", "Ben", "Callum", "Dario", "Eli", "Felix", "Gabriel", "Hugo", "Ivan", "Jonah",
    "Kofi", "Luca", "Marco", "Nico", "Oscar", "Pablo", "Rafael", "Sami", "Theo", "Yusuf",
]  # fmt: skip
SURNAME_START = [
    "Ash", "Brem", "Cad", "Dorr", "Elm", "Fenn", "Gald", "Hask", "Ivel", "Jorr", "Kest",
    "Lanv", "Morr", "Orv", "Pell", "Rask", "Sorr", "Tarv", "Varr", "Wend", "Yarr",
]  # fmt: skip
SURNAME_END = [
    "away", "bury", "cott", "dane", "enby", "holm", "ick", "lowe", "mere", "nell", "ock",
    "rigg", "sall", "ver", "wick",
]  # fmt: skip


@dataclass(frozen=True)
class SimPlayer:
    id: str
    name: str
    shirt: int
    position: Position
    slot: tuple[float, float]  # (u, v) in the team's attacking frame, see params.FORMATION_4231
    params: TrueParams
    test_values: ClubTestValues | None
    starter: bool = True

    def info(self, club_tests: bool) -> PlayerInfo:
        return PlayerInfo(
            id=self.id,
            name=self.name,
            shirt=self.shirt,
            position=self.position,
            starter=self.starter,
            test_values=self.test_values if club_tests else None,
        )


@dataclass(frozen=True)
class SimTeam:
    id: str
    name: str
    side: str
    formation: str
    attacks_positive_x_in_period_1: bool
    players: list[SimPlayer]
    pass_success: float  # base pass completion before distance and pressure
    press_chance: float  # chance of a high press when the opponent builds up

    def info(self, club_tests: bool, bench: tuple[SimPlayer, ...] = ()) -> TeamInfo:
        """The starters, then ``bench``: the substitutes who came on."""
        return TeamInfo(
            id=self.id,
            name=self.name,
            side=self.side,
            formation=self.formation,
            attacks_positive_x_in_period_1=self.attacks_positive_x_in_period_1,
            players=[p.info(club_tests) for p in [*self.players, *bench]],
        )


@dataclass(frozen=True)
class SubPlan:
    """A planned substitution: from ``clock_s`` on the match clock (45:00 or earlier: at
    half-time), at the next stoppage, ``player`` replaces the one in engine slot ``slot``."""

    team: int
    slot: int  # engine index 0–21
    clock_s: float
    player: SimPlayer


def _clipped_normal(rng: np.random.Generator, mean: float, sd: float, lo_hi) -> float:
    return float(np.clip(rng.normal(mean, sd), *lo_hi))


def true_params(rng: np.random.Generator, prior: dict | None = None) -> TrueParams:
    """Hidden physiology of one player (synthesis §3.2.3, §3.2.4, §3.6). ``prior`` overrides
    the CS, D′ and pool settings (``params.VARY_PLAYERS``); the draws are the same either way."""
    q = prior or {}
    cs_sd, cs_range = q.get("cs_sd", P.CS_SD), q.get("cs_range", P.CS_RANGE)
    dp_sd, dp_range = q.get("d_prime_sd", P.D_PRIME_SD), q.get("d_prime_range", P.D_PRIME_RANGE)
    return TrueParams(
        cs=round(_clipped_normal(rng, P.CS_MEAN, cs_sd, cs_range), 3),
        d_prime=round(_clipped_normal(rng, P.D_PRIME_MEAN, dp_sd, dp_range), 1),
        a0=round(_clipped_normal(rng, P.A0_MEAN, P.A0_SD, P.A0_RANGE), 3),
        s0=round(_clipped_normal(rng, P.S0_MEAN, P.S0_SD, P.S0_RANGE), 3),
        fast_fraction=round(
            float(rng.uniform(*q.get("fast_fraction_range", P.FAST_FRACTION_RANGE))), 3
        ),
        tau_fast=round(float(rng.uniform(*q.get("tau_fast_range", P.TAU_FAST_RANGE))), 1),
        tau_slow=round(float(rng.uniform(*q.get("tau_slow_range", P.TAU_SLOW_RANGE))), 1),
    )


def club_test_values(rng: np.random.Generator, truth: TrueParams) -> ClubTestValues:
    """Truth plus a normal measurement error on each value (params.TEST_ERROR_SD)."""

    def measured(name: str, ndigits: int) -> float:
        sd = P.TEST_ERROR_SD[name]
        error = float(np.clip(rng.normal(0.0, sd), -3 * sd, 3 * sd))
        return round(getattr(truth, name) * (1 + error), ndigits)

    return ClubTestValues(
        cs=measured("cs", 2),
        d_prime=measured("d_prime", 0),
        a0=measured("a0", 2),
        s0=measured("s0", 2),
    )


def _player_name(rng: np.random.Generator, used: set[str]) -> str:
    while True:
        name = f"{rng.choice(FIRST_NAMES)} {rng.choice(SURNAME_START)}{rng.choice(SURNAME_END)}"
        if name not in used:
            used.add(name)
            return name


def make_teams(rng: np.random.Generator, prior: dict | None = None) -> list[SimTeam]:
    """Home and away teams, both 4-2-3-1. Ids are H01–H11 and A01–A11 in formation order."""
    places = rng.choice(len(PLACES), size=2, replace=False)
    home_attacks_positive_x = bool(rng.random() < 0.5)
    used: set[str] = set()
    teams = []
    for side, place in zip(["home", "away"], places, strict=True):
        shirts = {pos: list(numbers) for pos, numbers in P.SHIRTS.items()}
        players = []
        for i, (pos, u, v) in enumerate(P.FORMATION_4231, start=1):
            truth = true_params(rng, prior)
            players.append(
                SimPlayer(
                    id=f"{side[0].upper()}{i:02d}",
                    name=_player_name(rng, used),
                    shirt=shirts[pos].pop(0),
                    position=pos,
                    slot=(u, v),
                    params=truth,
                    test_values=None if pos == Position.GK else club_test_values(rng, truth),
                )
            )
        teams.append(
            SimTeam(
                id=side,
                name=f"{PLACES[place]} {rng.choice(SUFFIXES)}",
                side=side,
                formation="4-2-3-1",
                attacks_positive_x_in_period_1=home_attacks_positive_x == (side == "home"),
                players=players,
                pass_success=float(rng.normal(P.PASS_BASE_SUCCESS, P.PASS_SUCCESS_TEAM_SD)),
                press_chance=float(rng.uniform(*P.PRESS_CHANCE)),
            )
        )
    return teams


def plan_substitutions(
    rng: np.random.Generator, teams: list[SimTeam], prior: dict | None = None
) -> list[SubPlan]:
    """Each team's substitutes (params, "Substitutions"): how many, the windows, and who goes
    off, like for like. A substitute gets their own hidden values and club test values. Ids
    H12–H16 and A12–A16, shirts 12–16, in the order they are planned."""
    used = {p.name for team in teams for p in team.players}
    plans = []
    for k, team in enumerate(teams):
        n = int(rng.choice(P.SUBS_CHOICES, p=P.SUBS_WEIGHTS))
        windows = sorted(
            float(np.clip(rng.normal(mean, sd), *P.SUB_WINDOW_CLIP))
            for mean, sd in zip(P.SUB_WINDOWS_MIN, P.SUB_WINDOW_SD, strict=True)
        )
        weight = np.array([P.SUB_WEIGHT[p.position] for p in team.players])
        number = 12
        for minute, count in zip(windows, P.SUBS_PER_WINDOW[n], strict=True):
            clock = 45.0 * 60.0 if minute < P.HALF_TIME_SUB_BEFORE else minute * 60.0
            for _ in range(count):
                j = int(rng.choice(11, p=weight / weight.sum()))
                weight[j] = 0.0  # a slot is substituted once
                off = team.players[j]
                truth = true_params(rng, prior)
                player = SimPlayer(
                    id=f"{team.side[0].upper()}{number:02d}",
                    name=_player_name(rng, used),
                    shirt=number,
                    position=off.position,
                    slot=off.slot,
                    params=truth,
                    test_values=club_test_values(rng, truth),
                    starter=False,
                )
                plans.append(SubPlan(k, 11 * k + j, clock, player))
                number += 1
    return sorted(plans, key=lambda s: (s.clock_s, s.slot))
