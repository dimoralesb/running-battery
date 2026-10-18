"""MCP server over one match (PLAN §4): the agents' only window on the data.

``python -m secondwind.agents.mcp_server <match folder>`` (stdio). The folder needs
``metadata.json``, ``events.jsonl``, ``tracking.jsonl`` and the estimator's ``signals.json``;
the truth file is never read. All tools are read-only and return numbers as
``{"value", "unit", "source"}`` (``agents.tools``).
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Any, Literal

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from secondwind.agents.tools import MOMENT_KINDS, MatchTools

READ_ONLY = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True)
Kind = Literal[
    "red_zone", "exposed_on_turnover", "second_wind", "fresh_legs", "not_tired_tactical",
    "tug_of_war", "flat_out",
]  # fmt: skip


def build(folder: Path | str) -> FastMCP:
    tools = MatchTools(folder)
    server = FastMCP(
        "secondwind",
        log_level="WARNING",
        instructions=(
            "Second Wind: read-only tools over one synthetic football match. Numbers come with "
            "their unit and source field. The battery and the typical-pro chance describe the "
            "running relative to a typical professional, never the player's own state."
        ),
    )

    @server.tool(annotations=READ_ONLY)
    def match_summary() -> dict[str, Any]:
        """Teams, line-ups, score timeline, substitutions and period lengths."""
        return tools.match_summary()

    @server.tool(annotations=READ_ONLY)
    def player_signals(
        player: str, start: str | None = None, end: str | None = None
    ) -> dict[str, Any]:
        """One player's signals over a window (from ``start`` to ``end``, match clock such as
        "20:00", "45+2:00" or "67:30"; default his whole time on the pitch): battery for a
        typical professional with its band, the typical-pro chance with its calibration note,
        energy, high-speed running in the last 1/2/5 min and vs his own peak and match average,
        red-zone and post-peak flags. ``player``: id ("H04"), name, or "home 3"."""
        return tools.player_signals(player, start, end)

    @server.tool(annotations=READ_ONLY)
    def find_moments(kind: Kind, limit: int = 10, player: str | None = None) -> dict[str, Any]:
        """Story moments, ranked best first: red_zone (a red-zone spell), exposed_on_turnover (a
        defender catching breath when his team loses the ball), second_wind (back to normal
        after a spell), fresh_legs (a substitute's first minutes), not_tired_tactical (running
        dropped while a non-fatigue reason fits), tug_of_war (team level: one team ran much
        harder per ball-in-play minute, or a gap closed), flat_out (a run at or near a player's
        top speed so far). Each moment lists its facts and the claims register rows that may
        describe it; team moments have a team instead of a player."""
        return tools.find_moments(kind, limit, player)

    @server.tool(annotations=READ_ONLY)
    def team_running(start: str | None = None, end: str | None = None) -> dict[str, Any]:
        """Both teams' running per ball-in-play minute, with and without the ball, over a window
        (match clock, default the whole match) and in 15-min blocks. Measured running only:
        which team is more tired is not measurable from positions (claim 35)."""
        return tools.team_running(start, end)

    @server.tool(annotations=READ_ONLY)
    def moment_context(
        t: str, period: int | None = None, player: str | None = None, team: str | None = None
    ) -> dict[str, Any]:
        """What else could explain the running at match time ``t``: ball in play, score and
        lead, minutes into the half, possession and whether the team just lost or won the ball,
        just substituted on, first-half load. ``non_fatigue_reasons`` must be named (or neutral
        words used) before any sentence says "tired" or "fatigue"."""
        return tools.moment_context(t, period, player, team)

    @server.tool(annotations=READ_ONLY)
    def claim(claim_id: str) -> dict[str, Any]:
        """One row of the claims register (synthesis §5): status, sources, qualifier, allowed
        wording and mode; or a global rule (G1–G5, G9)."""
        return tools.claim(claim_id)

    @server.tool(annotations=READ_ONLY)
    def verify(
        sentence: str,
        mode: Literal["fan", "analyst"] = "fan",
        context: dict[str, Any] | None = None,
        claim_id: str | None = None,
    ) -> dict[str, Any]:
        """The rule-based Verifier: blocks a sentence the claims register does not allow. Pass
        the moment's context (with its facts) to run the context and numbers checks too."""
        return tools.verify(sentence, mode, context, claim_id)

    return server


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m secondwind.agents.mcp_server")
    parser.add_argument("folder", type=Path, nargs="?", default=os.environ.get("SECONDWIND_MATCH"))
    args = parser.parse_args(argv)
    if args.folder is None:
        parser.error("give a match folder (or set SECONDWIND_MATCH)")
    build(args.folder).run("stdio")


assert set(Kind.__args__) == set(MOMENT_KINDS)  # type: ignore[attr-defined]

if __name__ == "__main__":
    main()
