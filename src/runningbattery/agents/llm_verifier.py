"""The Verifier's second pass: an LLM reads each sentence the rules let through and
checks it against the claim it cites, the whole register and the moment's context.

Order: the rules first (``verifier.verify``); they can only block. Then the LLM, which can
only block too, and may offer a rewrite (checked again by both passes before it is used). If the
LLM step fails or times out, the rule verdict stands and ``stage`` says so.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel

from runningbattery.agents import verifier

TIMEOUT_S = 60.0


class LLMVerdict(BaseModel):
    # Written before the verdict (prompt revision 4): each statement set against the facts.
    fact_check: str = ""
    verdict: Literal["pass", "block"]
    rule: str | None = None  # register id of the claim or global rule it breaks
    reason: str
    rewrite: str | None = None


@dataclass
class FullVerdict:
    sentence: str
    ok: bool
    stage: str  # "rules", "llm", "rules (llm unavailable: …)"
    findings: list[dict] = field(default_factory=list)
    rewrite: str | None = None
    fact_check: str = ""  # the LLM's reading of the facts (prompt revision 4)


def instructions() -> str:
    """The register as the LLM Verifier's rulebook."""
    reg = verifier.register()
    rules = "\n".join(f"- {g['id']}: {g['rule']}" for g in reg["global_rules"])
    rows = []
    for c in reg["claims"]:
        line = f"- {c['id']} [{c['status']}"
        line += f", {c['mode']} mode" if c.get("mode") else ""
        line += f"] {c['pattern']}."
        if c.get("qualifier"):
            line += f" Qualifier: {c['qualifier']}"
        if c.get("wording"):
            line += f' Allowed wording: "{c["wording"]}"'
        if c.get("alternative"):
            line += f' Instead say: "{c["alternative"]}"'
        rows.append(line)
    return f"""You are the Verifier of Running Battery, a football commentary system. Sentences
about a synthetic match go on screen only if you pass them. The rules below come from published
sports science (the claims register). A fixed rule checker has already passed the sentence;
you catch what patterns miss: paraphrases, implications and context.

What the system can know: from player positions alone it measures the running (distance,
high-speed running, energy, his hardest minutes, output vs the player's own match average, ball in
play) and estimates what that running would cost a TYPICAL PROFESSIONAL (a "battery" share of a
typical professional's short-term reserve, and the chance a typical professional would be below
half of it). It can NEVER know how tired this particular player is, his fitness, his physiology, his
intentions or his mental state.

Global rules:
{rules}
- N1: every number must come from the facts given (a rounding, percentage or km/h of one), or
  from the cited claim's wording. The numbers in the wordings of claims 11, 12 and 13 ("about
  40%", "13 km", "a 3–0 lead") are examples: the real number must be in the facts.
- F1: what the sentence says must agree with the facts given: "the lowest point of his match"
  needs the current value to be the lowest so far, "more than his team-mates" needs the facts to
  show more, and a moment of recovery must not be described as a drop. Block a sentence the
  facts contradict. Before the verdict, write "fact_check": take each statement in the sentence
  and set it against the facts: the direction of every comparison (above or below, more or
  less, faster or slower, nearer or further, dropped or recovered), every superlative ("fastest
  so far", "most", "lowest") and every reason given for a change. A reason offered for a change
  the facts do not show contradicts them. Saying fatigue is part of the reason ("not only
  fatigue", "partly fatigue") is a statement about the player's own state (claim 33). With no
  facts, write "no facts". F1 blocks only what the facts contradict: a statement the facts do
  not mention is not a contradiction (unsourced numbers are N1's job), and the moment's own
  name for its window ("just after his hardest minutes so far") needs no fact.
- G3 in practice: if the context lists non-fatigue reasons, a sentence that blames fatigue
  ("tired", "fatigue", "in the red", "his legs have gone", "running out of steam"...) must name
  one of them, or use neutral words.

Claims register (status: supported, qualified = only with its qualifier, blocked = never, in any
wording; analyst-mode rows are blocked in fan mode):
{chr(10).join(rows)}

Block a sentence (verdict "block") only if it breaks a specific rule or claim above, in letter
or in meaning, including any paraphrase or implication of a blocked claim (a player's own
tiredness, emptiness or fitness; errors, misses or decisions blamed on fatigue; winning because
of running; physiology such as lactate or heart rate). Give that id in "rule" and say why in one
sentence. If you can, give a "rewrite" that keeps the same moment but complies, uses only the
given facts and the register's wordings, and keeps m/s before km/h.

How to read the rules (do not block for these):
- The typical-professional wording ("a typical professional would...", "running that would leave
  a typical professional at about X%") IS the estimate language that G2, G9 and claim 11 ask for.
  In fan mode the band and the calibration are shown next to the sentence; it need not repeat
  them.
- N1 applies only when facts are given in the context; with no facts, do not check numbers.
- Ruling fatigue out ("not fatigue", "rather than fatigue") because a non-fatigue reason fits is
  what claim 13 asks for; it is not a claim about the player's own state.
- G5 is about phases of play (with or without the ball, ball in play), not halves or minutes.
- "His hardest minutes (so far)" and "just after his hardest minutes (so far)" are the system's
  neutral names for measured windows (his high-speed running at its peak, and the minutes after
  it, the post-peak flag), not claims about his physiology or his own tiredness.
- The moments' names are football's names for kinds of moment, not claims about anyone's body
  or tiredness (prompt revision 6): "second wind" (his running back up after his hardest
  minutes), "fresh legs" (a substitute's running against his team-mates'), "caught on the
  break" (his team lost the ball just after his hardest minutes), "quiet spell" (little running,
  with the reason given), "hardest minutes", "flat out" and "who's doing the running".
- Measured facts about one player's running (distance, high-speed running vs his own match
  average or peak, his hardest minutes, speeds, energy used) are facts, not physiology.

Pass (verdict "pass") sentences that state measured facts as facts, general findings in the
register's words, or the typical-professional wording, even if they are plain. Do not block for
style. Answer in JSON only."""


async def llm_check(
    agent, sentence: str, mode: str, context: dict | None, claim_id: str | None
) -> LLMVerdict:
    cited = ""
    if claim_id:
        row = next((c for c in verifier.register()["claims"] if c["id"] == str(claim_id)), None)
        cited = json.dumps(row, ensure_ascii=False) if row else f"unknown claim {claim_id}"
    facts = "" if context and "facts" in context else "\nNo facts were given: skip N1."
    prompt = (
        f"Mode: {mode}\nSentence: {sentence}\nCited claim: {cited or 'none'}\n"
        f"Context and facts (JSON): {json.dumps(context or {}, ensure_ascii=False)}{facts}"
    )
    r = await agent.run(prompt, options={"response_format": LLMVerdict})
    return r.value


async def verify_full(
    sentence: str,
    mode: str = "fan",
    context: dict | None = None,
    claim_id: str | None = None,
    agent=None,
    timeout: float = TIMEOUT_S,
) -> FullVerdict:
    """Rules, then the LLM (if ``agent`` is given)."""
    v = verifier.verify(sentence, mode, context, claim_id)  # type: ignore[arg-type]
    found = [{"claim": f.claim, "message": f.message, "stage": "rules"} for f in v.findings]
    if not v.ok:
        return FullVerdict(sentence, False, "rules", found)
    if agent is None:
        return FullVerdict(sentence, True, "rules")
    try:
        lv = await asyncio.wait_for(llm_check(agent, sentence, mode, context, claim_id), timeout)
    except Exception as e:  # the rule verdict stands
        return FullVerdict(sentence, True, f"rules (llm unavailable: {type(e).__name__})")
    if lv is None:
        return FullVerdict(sentence, True, "rules (llm unavailable: no answer)")
    if lv.verdict == "block":
        finding = {"claim": lv.rule or "?", "message": lv.reason, "stage": "llm"}
        return FullVerdict(sentence, False, "llm", [finding], lv.rewrite, lv.fact_check)
    return FullVerdict(sentence, True, "llm", fact_check=lv.fact_check)


def verifier_agent():
    from runningbattery.agents import foundry

    return foundry.agent("Verifier", instructions(), "main")
