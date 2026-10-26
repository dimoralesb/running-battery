"""Story controls (PLAN §2.3): seeded settings that make a demo match tell a story on purpose.

Story matches are for the demo only. They over-represent the moments the agents explain, so
they are never used for validation numbers (PLAN §2.6, point 4).

A story changes what the teams *try* to do, never the physiology: the fade after a high press
comes from the same pools and tank as in any match (synthesis §9.4, "story controls tied to
physiology"). ``python -m runningbattery.sim --seed 11 --story press-fade --out …``

- **High press, then fade.** Until ``press_until_min`` the pressing team presses whenever the
  opponent builds up (``press_chance``, against the 0.25–0.55 of a team's own style,
  ``params.PRESS_CHANCE``), and its forwards and central midfielders close the carrier down more
  often (``press_run_boost`` on ``PRESS_RUN_CHANCE`` and ``MID_PRESS_CHANCE``), and its
  players run with a higher work rate in play (``press_effort`` on ``POSITION_EFFORT``, like the
  shared tempo). After that the team goes back to its own style.
- **A full-back exposed on the turnover.** In the opponent's positive transitions, passes to
  team-mates within ``counter_reach`` metres of the exposed player are ``counter_bias`` times as
  likely: the counter goes at his side.
- **A fresh substitute.** One of the team's planned substitutes (the one planned closest to
  ``sub_minute``) replaces the exposed full-back instead, at ``sub_minute``; the substitute's
  hidden values are the ones already drawn for that plan.

All values are our assumptions, chosen to make the moments visible in one match. Decision 44:
``press_effort`` 1.06 → 1.02 from a scripted search (``press_chance`` 0.6–0.9 × ``press_effort``
1.00–1.06 × ``press_run_boost`` 1.25–1.75, each point on the demo seed and 5 more): at 1.06 one
15-min block of the demo match had the pressing team 79% ahead on high-speed running per
ball-in-play minute, beyond the 7 IDSSE matches' largest (46%), and 4 of the 6 seeds went past
46%. The rule, fixed before the results: the demo match below 46% with every story moment (the
press team ahead in 2 of the first hour's blocks, a player caught on the break 3 times, a
substitute with fresh legs, all 7 moment kinds), at most 1 of the 6 seeds above 46%, and of
those the point nearest the old values. Now 27% at most, 1 seed of 6 above 46%.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace

from runningbattery.sim.rosters import SimTeam, SubPlan


@dataclass(frozen=True)
class Story:
    name: str
    press_team: int = 0  # 0 home, 1 away
    press_chance: float = 0.9
    press_until_min: float = 60.0
    press_run_boost: float = 1.75
    press_effort: float = 1.02  # decision 44: scripted search (module docstring)
    exposed_slot: int = 3  # engine index: home slot 4 (H04), the left-back (FORMATION_4231)
    counter_bias: float = 4.0
    counter_reach: float = 20.0
    sub_minute: float | None = 66.0  # None: no story substitution

    def settings(self) -> dict[str, str | float | int | bool]:
        """For truth.json ``story``."""
        return {k: v for k, v in asdict(self).items() if v is not None}

    def pressing(self, team: int, clock_s: float) -> bool:
        return team == self.press_team and clock_s < self.press_until_min * 60.0


STORIES = {"press-fade": Story("press-fade")}


def story_subs(plans: list[SubPlan], teams: list[SimTeam], story: Story) -> list[SubPlan]:
    """The planned substitutions with the story's one: the exposed player off at
    ``sub_minute``, like for like."""
    if story.sub_minute is None:
        return plans
    team = story.exposed_slot // 11
    mine = [p for p in plans if p.team == team]
    if not mine:
        return plans
    same = [p for p in mine if p.slot == story.exposed_slot]
    pick = same[0] if same else min(mine, key=lambda p: abs(p.clock_s - story.sub_minute * 60))
    off = teams[team].players[story.exposed_slot % 11]
    player = replace(pick.player, position=off.position, slot=off.slot)
    new = SubPlan(team, story.exposed_slot, story.sub_minute * 60.0, player)
    return sorted([p for p in plans if p is not pick] + [new], key=lambda s: (s.clock_s, s.slot))
