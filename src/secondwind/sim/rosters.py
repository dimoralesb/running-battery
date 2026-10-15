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

    def info(self) -> PlayerInfo:
        return PlayerInfo(
            id=self.id,
            name=self.name,
            shirt=self.shirt,
            position=self.position,
            starter=True,
            test_values=self.test_values,
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

    def info(self) -> TeamInfo:
        return TeamInfo(
            id=self.id,
            name=self.name,
            side=self.side,
            formation=self.formation,
            attacks_positive_x_in_period_1=self.attacks_positive_x_in_period_1,
            players=[p.info() for p in self.players],
        )


def _clipped_normal(rng: np.random.Generator, mean: float, sd: float, lo_hi) -> float:
    return float(np.clip(rng.normal(mean, sd), *lo_hi))


def true_params(rng: np.random.Generator) -> TrueParams:
    """Hidden physiology of one player (synthesis §3.2.3, §3.2.4, §3.6)."""
    return TrueParams(
        cs=round(_clipped_normal(rng, P.CS_MEAN, P.CS_SD, P.CS_RANGE), 3),
        d_prime=round(_clipped_normal(rng, P.D_PRIME_MEAN, P.D_PRIME_SD, P.D_PRIME_RANGE), 1),
        a0=round(_clipped_normal(rng, P.A0_MEAN, P.A0_SD, P.A0_RANGE), 3),
        s0=round(_clipped_normal(rng, P.S0_MEAN, P.S0_SD, P.S0_RANGE), 3),
        fast_fraction=round(float(rng.uniform(*P.FAST_FRACTION_RANGE)), 3),
        tau_fast=round(float(rng.uniform(*P.TAU_FAST_RANGE)), 1),
        tau_slow=round(float(rng.uniform(*P.TAU_SLOW_RANGE)), 1),
    )


def club_test_values(rng: np.random.Generator, truth: TrueParams) -> ClubTestValues:
    """Truth with a 5–10% error of random sign on each value (PLAN §3.2)."""

    def measured(value: float, ndigits: int) -> float:
        error = rng.uniform(*P.TEST_ERROR_RANGE) * rng.choice([-1.0, 1.0])
        return round(float(value * (1 + error)), ndigits)

    return ClubTestValues(
        cs=measured(truth.cs, 2),
        d_prime=measured(truth.d_prime, 0),
        a0=measured(truth.a0, 2),
        s0=measured(truth.s0, 2),
    )


def _player_name(rng: np.random.Generator, used: set[str]) -> str:
    while True:
        name = f"{rng.choice(FIRST_NAMES)} {rng.choice(SURNAME_START)}{rng.choice(SURNAME_END)}"
        if name not in used:
            used.add(name)
            return name


def make_teams(rng: np.random.Generator) -> list[SimTeam]:
    """Home and away teams, both 4-2-3-1. Ids are H01–H11 and A01–A11 in formation order."""
    places = rng.choice(len(PLACES), size=2, replace=False)
    home_attacks_positive_x = bool(rng.random() < 0.5)
    used: set[str] = set()
    teams = []
    for side, place in zip(["home", "away"], places, strict=True):
        shirts = {pos: list(numbers) for pos, numbers in P.SHIRTS.items()}
        players = []
        for i, (pos, u, v) in enumerate(P.FORMATION_4231, start=1):
            truth = true_params(rng)
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
