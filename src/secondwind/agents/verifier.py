"""The rule-based Verifier (PLAN §3.4; BUILD_PLAN "Wed 21"): fixed checks that run before any
LLM check, so unsupported claims are blocked even if the LLM Verifier slips.

``python -m secondwind.agents.verifier "He is tired." [--mode analyst]``

Each rule is tied to a row of the claims register (``claims.json``, from synthesis §5): a
blocked claim (20–34), a qualified claim used without its qualifier (10, 11, 17, 19c, 19d), an
analyst-only claim in fan mode (9c, 16, 18, 19, 19d), or a global rule (G1 baseline for every
percentage, G2 estimate language, G9 typical-professional wording). A sentence passes only if no
rule fires. The checks read the sentence alone; the context check (G3: ball in play, score,
start of a half) needs the match data and belongs to the agent that writes the sentence.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Literal

Mode = Literal["fan", "analyst"]
REGISTER = Path(__file__).with_name("claims.json")
FLAGS = re.IGNORECASE

# Words that make a sentence a statement about fatigue or the battery.
FATIGUE = (
    r"\b(tired|tiring|fatigu\w*|exhaust\w*|knackered|shattered|leggy|in the tank|in the red|"
    r"battery|reserve|running on empty|out of gas|heavy legs|tired legs|dead legs|"
    r"legs (?:had|have) gone)\b"
)
# Estimate language (G2) or the typical-professional wording (claim 11).
HEDGE = (
    r"\b(likely|probably|our estimate|we estimate|estimated?|the data suggest|suggests?|"
    r"typical professional|typical pro|model|may|might|could|in general|typically)\b"
)
# A reference to one player (G2 applies to statements about a player, not general ones).
PERSON = r"\b(he|she|him|his|her|he's|she's)\b"
# A capitalised name as the subject (not a sentence-opening function word).
NAME = r"\b(?!(?:This|That|It|There|Here|What|Which|Who|The|A|An|In|After|When)\b)[A-Z][a-z]+"
STATE = r"(tired|exhausted|fatigued|knackered|spent|shattered|out on his feet|done in)"
# Baselines that make a percentage meaningful (G1, claim 24).
BASELINE = (
    r"\b(than|vs\.?|versus|compared (?:with|to)|match average|average|normal|usual|peak|"
    r"first 15|kick-off|first half|reserve|typical professional|of the time|chance|earlier)\b"
)
NEGATED_LACTIC = r"\b(isn'?t|is not|not|no|nothing to do with)\b[^.]{0,25}\blactic"


@dataclass(frozen=True)
class Rule:
    claim: str  # claims register id ("33", "G1", …)
    message: str
    pattern: str  # fires when found…
    needs: str | None = None  # …and this is found too
    unless: str | None = None  # …and this is not found
    fan_only: bool = False  # only blocks in fan mode (analyst-only claims)


RULES: tuple[Rule, ...] = (
    # 33: the player's own state.
    Rule("33", "About the player's own state; say what the running would cost a typical "
         "professional (claim 11)",
         rf"(\b(he|she|they)\s*(is|'s|’s|are|was|were|looks?|seems?|appears?)|{NAME}\s+"
         rf"(is|was|looks|seems))\s+(\w+\s+)?{STATE}\b"),
    Rule("33", "A percentage of the player himself; say what it would leave a typical "
         "professional", r"\b(he|she|he's|she's)\s*(is|'s|’s|was)?\s*(at|down to|on)\s+"
         r"(about\s+)?\d+\s*(%|percent)"),
    Rule("33", "The player's battery; say what the running would leave a typical professional",
         r"\b(his|her|their)\s+battery\b", unless=r"typical professional"),
    Rule("33", "\"Running on empty\" is about the player's own state",
         r"running on empty|out of gas|on fumes|nothing left in the tank"),
    Rule("19c", "Never \"empty\" or \"exhausted\" from the battery (claim 19c)",
         r"\b(battery|tank|reserve)\b[^.]*\b(empty|drained|flat|dead)\b"),
    Rule("G9", "A share of the player's own reserve; use the typical-professional wording",
         r"\d+\s*(%|percent)\s+of\s+(his|her|their own)\s+(reserve|battery|D′|D')"),
    # 20–22: errors blamed on fatigue.
    Rule("20", "Pass accuracy holds up under fatigue in matches (claim 20)",
         r"(misplac\w*|wayward|sloppy|errant|stray|poor|bad|loose)\s+(pass|touch)|"
         r"gave (the ball|it|possession) away|misplaced", needs=FATIGUE),
    Rule("21", "Decisions and concentration are not shown to fail with fatigue (claim 21)",
         r"(bad|poor|wrong|rash)\s+decision|lost (his |her )?concentration|switched off|"
         r"mental lapse", needs=FATIGUE),
    Rule("22", "Shooting success is unchanged with fatigue (claim 22)",
         r"missed (the|a|his|her|that) (shot|chance|sitter|header)|shot (wide|over)|skied",
         needs=FATIGUE),
    Rule("23", "Intense accelerations are not suppressed after peaks (claim 23)",
         r"can(no|'|’)?t accelerate|unable to accelerate|lost (his|her) acceleration|"
         r"no acceleration left"),
    # 24 / G1: percentages.
    Rule("24", "A percentage without its baseline (vs his match average, vs his peak, vs the "
         "first 15 min)", r"\d+\s*(%|percent)", unless=BASELINE),
    Rule("24", "A drop this large is vs the peak, not \"below normal\" (claim 24)",
         r"\b([6-9]\d|100)\s*(%|percent)[^.]*\b(less than|below|under)\s+(his |her |their )?"
         r"(normal|usual|match average|average)"),
    # 25–29.
    Rule("25", "Lactate does not track temporary fatigue (claim 25)", r"\blact(ic|ate)\b",
         unless=NEGATED_LACTIC),
    Rule("26", "Carry-over from earlier matches is not modelled (claim 26)",
         r"(from|after) (wednesday|tuesday|thursday|midweek|last week|the last|the previous)"
         r"('s)?\s*(match|game|fixture)|fixture congestion|midweek (match|game)",
         needs=FATIGUE),
    Rule("27", "No heart-rate data (claim 27)", r"\b(heart rate|pulse)\b|\b\d+\s*bpm\b"),
    Rule("28", "Not supported: role effects on space are small and similar (claim 28)",
         r"tired (forwards|strikers|attackers|wingers)[^.]*space|"
         r"(forwards|strikers) lose the most space"),
    Rule("29", "A player's physiology is assumed, never measured from tracking (claim 29)",
         r"\b(his|her|their)\s+(critical speed|CS|D′|D'|VO2 ?max|VO₂max|lactate threshold|"
         r"anaerobic threshold)\b[^.]*\d|critical speed (from|in) (this|the) (match|game)",
         unless=r"assumed|model parameter"),
    # 30–32, 34.
    Rule("30", "Winners outrun losers only slightly; no causal claim (claim 30)",
         r"\b(won|win|wins|beat)\b[^.]*\bbecause\b[^.]*\b(ran|run|running|outran|covered|"
         r"work rate)\b|\boutran\b[^.]*\b(so|and|which is why)\b[^.]*\b(won|win)\b|"
         r"\bran (more|further)\b[^.]*\bso\b[^.]*\b(won|win)\b"),
    Rule("31", "In-possession running goes with fewer points, not better play (claim 31)",
         r"ran (more|further) (with|in possession of) the ball[^.]*\b(better|won)\b"),
    Rule("32", "Acceleration counts differ ~10-fold between tracking systems (claim 32)",
         r"\baccelerations?\b[^.]*\b(than|above|below|compared (with|to))\b[^.]*"
         r"\b(league|published|premier league|norm|typical player|other players|average)\b"),
    Rule("34", "Running in a match does not show fitness (claim 34)",
         r"\b(ran|covered|running|distance)\b[^.]*(\b(so|which means|shows?|proves?)\b|:)[^.]*"
         r"\b(fitter|fittest|unfit|fitness)\b|\b(fitter|fittest|unfit)\b[^.]*"
         r"(\b(because|as)\b|:)[^.]*\b(ran|covered|running|distance)\b"),
    # Qualified claims used without their qualifier.
    Rule("10", "Top speed barely changes in matches; only \"a bit slower than earlier\" "
         "(claim 10)", r"lost (his|her) (pace|speed|legs)|no pace left|no legs left"),
    Rule("19d", "Never about one player's choices (claim 19d)",
         r"saving (himself|herself|his legs|her legs)|pacing (himself|herself)|conserving "
         r"(his|her) energy"),
    Rule("17", "Pitch control with fatigue is a model view (claim 17)", r"\bspace\b",
         needs=FATIGUE, unless=r"model|we estimate|estimate"),
    # G2: estimate language for statements about a player.
    Rule("G2", "Fatigue statements about a player need estimate language or the "
         "typical-professional wording", FATIGUE, needs=PERSON, unless=HEDGE),
    # Analyst-only claims in fan mode.
    Rule("16", "Lab-only finding: analyst mode only (claims 9c, 16, 19d)",
         r"\bin lab (tests|simulations)\b|\blab simulations\b", fan_only=True),
    Rule("18", "A weak association in one league: analyst mode only (claim 18)",
         r"\bin one league\b", fan_only=True),
    Rule("19", "Acceleration–speed profiles: analyst mode only, low confidence (claim 19)",
         r"acceleration(-|–| )?(speed )?profile", fan_only=True),
)  # fmt: skip


@dataclass(frozen=True)
class Finding:
    claim: str
    message: str


@dataclass(frozen=True)
class Verdict:
    sentence: str
    ok: bool
    findings: tuple[Finding, ...]


@cache
def register() -> dict:
    """The claims register (synthesis §5) as data."""
    return json.loads(REGISTER.read_text())


def _found(pattern: str, text: str) -> bool:
    return re.search(pattern, text, FLAGS) is not None


def verify(sentence: str, mode: Mode = "fan") -> Verdict:
    """Check one sentence against the fixed rules; ``ok`` only if none fires."""
    text = sentence.replace("’", "'")
    findings = []
    for rule in RULES:
        if rule.fan_only and mode != "fan":
            continue
        if not _found(rule.pattern, text):
            continue
        if rule.needs and not _found(rule.needs, text):
            continue
        if rule.unless and _found(rule.unless, text):
            continue
        findings.append(Finding(rule.claim, rule.message))
    return Verdict(sentence, not findings, tuple(dict.fromkeys(findings)))


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="python -m secondwind.agents.verifier", description=__doc__
    )
    parser.add_argument("sentences", nargs="+")
    parser.add_argument("--mode", choices=["fan", "analyst"], default="fan")
    args = parser.parse_args(argv)
    for s in args.sentences:
        v = verify(s, args.mode)
        print(("PASS  " if v.ok else "BLOCK ") + s)
        for f in v.findings:
            print(f"      claim {f.claim}: {f.message}")


if __name__ == "__main__":
    main()
