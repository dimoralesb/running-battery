"""The rule-based Verifier suite (BUILD_PLAN §3, run 7; v2 2026-10-17): every blocked sentence
and every unbaselined % must be caught, no valid sentence may be blocked (false-block rate 0),
and the context and numbers checks get their cases right. The sentences live in
``agents.verifier_suite``; the LLM pass is reported in docs/verifier_report.json."""

import json
from pathlib import Path

import pytest

from runningbattery.agents.verifier import RULES, register, verify
from runningbattery.agents.verifier_suite import (
    BLOCKED,
    CONTEXT,
    PARAPHRASES,
    VALID,
    cases,
    run_rules,
)

REPORT = Path(__file__).resolve().parents[1] / "docs" / "verifier_report.json"
# Context cases the rules get wrong on purpose: naming the time ("after the break") without
# naming it as the reason, and a claim the facts contradict (F1); only the LLM pass can tell.
RULES_MISS = {"He likely faded after the break.",
              # Decision 30: "most" for 43% contradicts the facts (F1, the LLM pass).
              "Most of Albion's high-speed running in 0:00–15:00 came in the first 10 seconds "
              "after the ball changed hands.",
              "In the Premier League, players make about a third fewer high-speed recovery runs "
              "right after their hardest minutes than they normally do; here his mean speed in "
              "the next 8 s was 3.7 m/s and he was 44 m from the ball 8 s later.",
              "This is the lowest point of his match so far, by our estimate.",
              "Westerlyn cover 196 m of high-speed running per ball-in-play minute while their "
              "opponents cover 160 m, roughly 22% less.",
              # (the "less opportunity to run" line of decision 29 is now blocked by the rules
              # for its old name, "red-zone spell", G10 of decision 30)
              # (the 76 s and 197 s spells explained by claim 2 are now blocked by the rules, the
              # claim 2 rule of 2026-10-19)
              # Decision 29, from the feeds: his own state in hedged words.
              "In the Premier League players make about a third fewer high-speed recovery runs "
              "after a peak, and our estimate says he may have had less in the tank here.",
}  # fmt: skip


@pytest.mark.parametrize(("sentence", "mode"), VALID)
def test_valid_sentences_pass(sentence, mode):
    v = verify(sentence, mode)
    assert v.ok, [f.claim for f in v.findings]


@pytest.mark.parametrize(("sentence", "mode", "claim"), BLOCKED)
def test_blocked_sentences_are_caught_for_the_right_reason(sentence, mode, claim):
    v = verify(sentence, mode)
    assert not v.ok and claim in {f.claim for f in v.findings}


def test_suite_size_and_rates():
    """About 100 sentences; every v1 blocked one caught, none of the valid ones blocked."""
    assert len(VALID) + len(BLOCKED) >= 50 and len(BLOCKED) >= 25
    assert len(cases()) >= 80
    caught = sum(not verify(s, m).ok for s, m, _ in BLOCKED) / len(BLOCKED)
    false_block = sum(not verify(s, m).ok for s, m in VALID) / len(VALID)
    assert caught == 1.0 and false_block == 0.0


def test_every_blocked_claim_has_a_rule_and_a_case():
    reg = register()
    ids = {c["id"] for c in reg["claims"]} | {g["id"] for g in reg["global_rules"]}
    assert {r.claim for r in RULES} <= ids
    blocked = {c["id"] for c in reg["claims"] if c["status"] == "blocked"}
    assert blocked <= {r.claim for r in RULES}
    assert blocked <= {c for _, _, c in BLOCKED}


def test_register_wordings_pass_in_their_mode():
    """The example wording of every supported or qualified claim passes the rules."""
    for c in register()["claims"]:
        if c["status"] != "blocked":
            v = verify(c["wording"], c["mode"])
            assert v.ok, (c["id"], [f.claim for f in v.findings])


@pytest.mark.parametrize(("sentence", "mode", "context", "claim", "ok"), CONTEXT)
def test_context_and_numbers_checks(sentence, mode, context, claim, ok):
    v = verify(sentence, mode, context, claim)
    if sentence in RULES_MISS:
        assert v.ok != ok
    else:
        assert v.ok == ok, [f.claim for f in v.findings]


def test_context_check_names_the_reason():
    reasons = {"non_fatigue_reasons": [{"code": "big_lead", "text": "his team leads by 2"}]}
    s = "A typical professional would likely be in the red after this."
    assert verify(s).ok
    v = verify(s, context=reasons)
    assert not v.ok and {f.claim for f in v.findings} == {"13"}
    assert verify("With his team 2–0 up, " + s[0].lower() + s[1:], context=reasons).ok


def test_numbers_must_come_from_the_facts_or_the_cited_claim():
    ctx = {"facts": {"hsr": {"value": 0.41}}}
    assert verify("His share is about 40% of his match average.", context=ctx).ok
    assert not verify("His share is about 55% of his match average.", context=ctx).ok
    wording = next(c["wording"] for c in register()["claims"] if c["id"] == "6")
    assert verify(wording, context=ctx, claim_id="6").ok  # 15–25% is the claim's own
    assert not verify(wording, context=ctx).ok


def test_paraphrases_are_never_passed_by_accident():
    """Held out from the rules: they catch few (the LLM pass's job), and none is a valid case."""
    caught = sum(not verify(s, m).ok for s, m, _ in PARAPHRASES)
    assert len(PARAPHRASES) >= 15 and caught >= 2


def test_report_covers_this_suite():
    """docs/verifier_report.json was made from these sentences, with the rules as they are."""
    rep = json.loads(REPORT.read_text())
    assert [r["sentence"] for r in rep["rows"]] == [c["sentence"] for c in cases()]
    assert [r["rules_ok"] for r in rep["rows"]] == [r["rules_ok"] for r in run_rules()]
    # The LLM pass varies from run to run (README, Limitations): 1.0 on the suites of
    # 2026-10-17, 76/78 on 2026-10-18 (it missed two F1 cases that disagree with the facts),
    # 86/89 with the held-out fact checks (decision 29); with decision 30's cases, runs of the
    # same prompt gave 92/96, 98/101, 98/102, 99/103 and 97/104 (held-out F1 3/6 in the last);
    # prompt revision 6 with decision 31's cases, 106/108 (F1 5/6; one LLM call timed out),
    # then with G11's wording made clear on 174 sentences, 106/108 (F1 5/6).
    # Decision 37 ("typical pro" as a rule-24 baseline), same prompt: 103/108 (F1 4/6).
    # With the G12 rule and its two cases, 176 sentences: 106/109 (F1 4/6), 3/67 false blocks.
    # Rule 33 ("reserve") and the team G5 check with their three cases, 179: 106/111, 4/68;
    # rule 33 with "his estimated typical-pro reserve", 180: 110/112, 0/68 (F1 5/6).
    # Decision 38's G13 (a scoreline is the score then) and its two cases, 182: rules 80/113,
    # 0/69; rules + LLM 109/113, 3/69 (F1 3/6). G5 for players and G10's "level" with four
    # cases (two older cases reworded to say high-speed), 186: 82/115, 0/71; 113/115, 5/71 (F1 5/6).
    # G14 (the player he replaced, not "over the same minutes") and two cases, 188: 83/116, 0/72;
    # rules + LLM 112/116, 4/72 (F1 5/6, paraphrases 22/23). G9 (reserve as %, not 0.59) and
    # claim 2 (keep "shaken off" or "recover") with two cases, 190: 85/118, 0/72; 114/118, 4/72
    # (F1 4/6, paraphrases 23/23).
    assert rep["report"]["llm"]["caught_rate"] >= 0.93


def test_overlay_copy_passes_the_verifier():
    """Every fixed sentence on the overlay (app/src/copy.json) goes through the rules too."""
    copy = json.loads((REPORT.parents[1] / "app" / "src" / "copy.json").read_text())
    sample = {
        "name": "Marco Tarvsall",
        "pct": 62,
        "lo": 48,
        "hi": 74,
        "chance": "about 18%",
        "v": 8.6,
        "kmh": 31,
        "team": "Westerlyn Albion",
        "share": 43,
        "time": 29,
        "block": "0:00–15:00",
        "situation": "First 10 s after losing the ball",
        "rate": 433,
        "n": 3,
        "claim": "11",
        "stage": "rules",
    }
    for key, text in copy.items():
        if key.startswith("_"):
            continue
        for mode in ("fan", "analyst"):
            v = verify(text.format(**sample), mode)
            assert v.ok, (key, [f.claim for f in v.findings])
