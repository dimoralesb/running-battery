"""Hidden physiology: each player's "true" fatigue, the ground truth (PLAN §2.3, layer 3).

Written to ``truth.json`` only; the estimator never sees it. Updated every frame (10 Hz) from
each player's own speed v, with their drawn CS, D′ and pool settings (``rosters.true_params``):

- **Two pools** [Chorley2023, Eq. 8a–8b; synthesis §3.2.4]. D′ is split into a fast pool
  (``fast_fraction`` of it) and a slow pool. Above CS both drain by (v − CS) metres per second,
  shared in proportion to what each holds (Eq. 8a). Below CS each refills towards full with its
  own time constant, which grows as v nears CS (Eq. 6b–6c, with %D = (CS − v)/CS × 100; speed in
  place of power is our adaptation, synthesis §3.2.2), scaled so that standing still it is the
  player's ``tau_fast`` or ``tau_slow``. The slow pool refills more slowly as the tank empties
  (``SLOW_TAU_PER_TANK``). The pools also refill over half-time (``HALF_TIME_S``).
- **Tank**: whole-match energy, 1 when fresh, falling by 1 per ``TANK_M`` metres run above CS;
  at half-time it gets back ``TANK_HALF_TIME_REFILL`` of what it lost.
- **Dip** at the start of the second half (``DIP``, ``DIP_S``).

What the state changes (params, "Hidden physiology and fatigue"):

- ``run_choice``: the chance that the player makes a hard run, pool term × tank × (1 − dip).
  The pools only limit running once they are low: the pool term is 1 while they hold at least
  ``POOL_FREE`` of D′ and falls in proportion below that, 1 − POOL_GAIN × (POOL_FREE − left) /
  POOL_FREE. The tank does not cut decisive sprints (``DECISIVE_EFFORT``).
  ``roles.Roles.start`` asks ``makes_run``; every hard-run decision that would have been a
  high-intensity run is kept (``decisions``), the skipped ones for ``truth.json``.
- short-term tiredness x = 1 − pool term: shorter runs (``shorten``), slower runs and ball
  roles (``speed_factor``), slower carries (``carry``), as after peak periods [Fang2024,
  Table 2, Fig. 1]. The tank does not slow runs: late in a match players make fewer hard runs,
  but match top speed barely changes [Bradley2009, p.163].
- ``speed_mult`` and ``accel_mult``: the player's capacity, S0 and A0, falling with the tank
  (``TOP_SPEED_PER_TANK``, ``ACCEL_PER_TANK``), at most ``CAPACITY_MAX_LOSS``.
- ``tired``: run_choice below ``TIRED_BELOW``.

The skip draws come from their own generator, so the match flow's draws do not depend on them
directly (the match still changes, because tired players move differently).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from secondwind.schema import Period, RunPurpose, TrueParams, TruthSeries
from secondwind.sim import params as P

REST = 100.0  # %D standing still


def tau_fast_curve(pct: np.ndarray) -> np.ndarray:
    """Fast-pool recharge time (s) at %D below CS [Chorley2023, Eq. 6b]."""
    return 45.0 * np.exp(-0.014 * pct) + 9999.0 * np.exp(-0.811 * pct)


def tau_slow_curve(pct: np.ndarray) -> np.ndarray:
    """Slow-pool recharge time (s) at %D below CS [Chorley2023, Eq. 6c]."""
    return 9999.0 * np.exp(-0.098 * pct) + 429.0


def below(level: np.ndarray, free: float, gain: float) -> np.ndarray:
    """1 while ``level`` is at least ``free``, then falling in proportion: at 0 it is 1 − gain
    (never below 0)."""
    return np.clip(1.0 - gain * np.maximum(free - level, 0.0) / free, 0.0, 1.0)


@dataclass(frozen=True)
class Decision:
    """A hard-run decision that would have been a high-intensity run: made or skipped."""

    player: int  # engine index 0–21
    period: int
    t_start: float  # s since the period's kick-off
    t_end: float  # its planned end
    purpose: RunPurpose
    made: bool


class Physiology:
    def __init__(self, params: list[TrueParams], rng: np.random.Generator):
        self.rng = rng
        get = lambda name: np.array([getattr(p, name) for p in params])  # noqa: E731
        self.cs = get("cs")
        self.d_prime = get("d_prime")
        self.fast_full = get("fast_fraction") * self.d_prime
        self.slow_full = self.d_prime - self.fast_full
        self.tau_fast = get("tau_fast")
        self.tau_slow = get("tau_slow")
        self.fast_m = self.fast_full.copy()  # metres left in each pool
        self.slow_m = self.slow_full.copy()
        self.tank = np.ones(len(params))
        self.dip = 0.0
        # Read here, not at import, so experiments can override params.
        self.s = {
            "tank_m": P.TANK_M,
            "tank_half_time_refill": P.TANK_HALF_TIME_REFILL,
            "slow_tau_per_tank": P.SLOW_TAU_PER_TANK,
            "dip": P.DIP,
            "dip_s": P.DIP_S,
            "pool_free": P.POOL_FREE,
            "pool_gain": P.POOL_GAIN,
            "hard_run_speed": P.HARD_RUN_SPEED,
            "decisive_effort": P.DECISIVE_EFFORT,
            "shape_decline_s": P.SHAPE_DECLINE_S,
            "shorten": P.SHORTEN,
            "slow": P.SLOW,
            "carry_slow": P.CARRY_SLOW,
            "top_speed_per_tank": P.TOP_SPEED_PER_TANK,
            "accel_per_tank": P.ACCEL_PER_TANK,
            "capacity_max_loss": P.CAPACITY_MAX_LOSS,
            "tired_below": P.TIRED_BELOW,
        }
        self.decisions: list[Decision] = []
        self.rows: list[np.ndarray] = []  # one (7, players) row per second, see ``series``
        self.periods: list[int] = []
        self.times: list[float] = []
        self.period = 1
        self.update_multipliers()

    def settings(self) -> dict[str, float]:
        """The effect sizes used, for ``truth.json``'s ``settings`` (PLAN §2.6, point 3)."""
        return dict(self.s)

    # --- State -------------------------------------------------------------------------------

    def start_period(self, period: int) -> None:
        """The second half follows a half-time rest: the pools refill standing still, the tank
        gets back a share of what it lost, and the dip starts."""
        self.period = period
        if period == 2:
            self.refill(np.zeros_like(self.cs), P.HALF_TIME_S)
            self.tank += self.s["tank_half_time_refill"] * (1.0 - self.tank)
        self.set_dip(0.0)
        self.update_multipliers()

    def set_dip(self, t: float) -> None:
        on = self.period == 2
        self.dip = self.s["dip"] * max(0.0, 1.0 - t / self.s["dip_s"]) if on else 0.0

    def refill(self, speed: np.ndarray, seconds: float) -> None:
        """Below CS each pool closes the gap to full with its time constant at this speed."""
        under = speed < self.cs
        pct = np.clip((self.cs - speed) / self.cs * 100.0, 0.0, REST)
        tau_f = self.tau_fast * tau_fast_curve(pct) / tau_fast_curve(REST)
        tau_s = self.tau_slow * tau_slow_curve(pct) / tau_slow_curve(REST)
        tau_s = tau_s * (1.0 + self.s["slow_tau_per_tank"] * (1.0 - self.tank))
        self.fast_m += np.where(
            under, (self.fast_full - self.fast_m) * -np.expm1(-seconds / tau_f), 0
        )
        self.slow_m += np.where(
            under, (self.slow_full - self.slow_m) * -np.expm1(-seconds / tau_s), 0
        )

    def step(self, speed: np.ndarray, t: float) -> None:
        """One frame at these speeds (m/s), ``t`` seconds into the period."""
        used = np.maximum(speed - self.cs, 0.0) * P.DT
        held = self.fast_m + self.slow_m
        share = np.divide(self.fast_m, held, out=np.full_like(held, 0.5), where=held > 0)
        self.fast_m = np.maximum(self.fast_m - used * share, 0.0)
        self.slow_m = np.maximum(self.slow_m - used * (1.0 - share), 0.0)
        self.refill(speed, P.DT)
        self.tank = np.maximum(self.tank - used / self.s["tank_m"], 0.0)
        self.set_dip(t)
        self.update_multipliers()

    def update_multipliers(self) -> None:
        s = self.s
        left = (self.fast_m + self.slow_m) / self.d_prime
        pools = below(left, s["pool_free"], s["pool_gain"])
        self.run_choice = pools * self.tank * (1.0 - self.dip)
        self.sprint_choice = pools * (1.0 - self.dip)  # decisive sprints: not cut by the tank
        self.tiredness = 1.0 - pools
        lost = 1.0 - self.tank
        cap = s["capacity_max_loss"]
        self.speed_mult = 1.0 - np.minimum(s["top_speed_per_tank"] * lost, cap)
        self.accel_mult = 1.0 - np.minimum(s["accel_per_tank"] * lost, cap)

    # --- Behaviour ---------------------------------------------------------------------------

    def makes_run(self, i: int, decisive: bool = False) -> bool:
        """Whether the player makes a hard run; a decisive sprint is not cut by the tank."""
        chance = self.sprint_choice[i] if decisive else self.run_choice[i]
        return bool(self.rng.random() < chance)

    def shorten(self, i: int) -> float:
        return 1.0 - self.s["shorten"] * float(self.tiredness[i])

    def speed_factor(self) -> np.ndarray:
        return 1.0 - self.s["slow"] * self.tiredness

    def carry(self, i: int) -> float:
        return 1.0 - self.s["carry_slow"] * float(self.tiredness[i])

    def decide(self, i: int, t: float, t_end: float, purpose: RunPurpose, made: bool) -> None:
        self.decisions.append(Decision(i, self.period, t, t_end, purpose, made))

    @property
    def skipped(self) -> list[Decision]:
        return [d for d in self.decisions if not d.made]

    # --- Truth -------------------------------------------------------------------------------

    def record(self, t: float) -> None:
        """Keep this frame's state as the value for second ``t`` (called once per second)."""
        self.periods.append(self.period)
        self.times.append(t)
        self.rows.append(
            np.stack(
                [
                    self.fast_m / self.fast_full,
                    self.slow_m / self.slow_full,
                    self.tank,
                    self.speed_mult,
                    self.accel_mult,
                    self.run_choice,
                    self.run_choice < self.s["tired_below"],
                ]
            )
        )

    def series(self, player: int) -> TruthSeries:
        """One player's 1 Hz series, rounded to 0.001."""
        rows = np.round(np.stack(self.rows)[:, :, player], 3) + 0.0
        period: list[Period] = self.periods  # type: ignore[assignment]
        return TruthSeries.model_construct(
            period=period,
            t=self.times,
            fast_pool=rows[:, 0].tolist(),
            slow_pool=rows[:, 1].tolist(),
            tank=rows[:, 2].tolist(),
            speed_mult=rows[:, 3].tolist(),
            accel_mult=rows[:, 4].tolist(),
            run_choice_mult=rows[:, 5].tolist(),
            tired=(rows[:, 6] > 0.5).tolist(),
        )
