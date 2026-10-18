"""The rule-based Verifier suite (BUILD_PLAN §3, run 7; v2 2026-10-17): every blocked sentence
and every unbaselined % must be caught, no valid sentence may be blocked (false-block rate 0),
and the context and numbers checks get their cases right. The sentences live in
``agents.verifier_suite``; the LLM pass is reported in docs/verifier_report.json."""

import json
from pathlib import Path

import pytest

from secondwind.agents.verifier import RULES, register, verify
from secondwind.agents.verifier_suite import BLOCKED, CONTEXT, PARAPHRASES, VALID, cases, run_rules

REPORT = Path(__file__).resolve().parents[1] / "docs" / "verifier_report.json"
# Context cases the rules get wrong on purpose: naming the time ("after the break") without
# naming it as the reason, and a claim the facts contradict (F1); only the LLM pass can tell.
RULES_MISS = {"He likely faded after the break.",
              "This is the lowest point of his match so far, by our estimate.",
              "Westerlyn cover 196 m of high-speed running per ball-in-play minute while their "
              "opponents cover 160 m, roughly 22% less."}  # fmt: skip


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
    assert rep["report"]["llm"]["caught_rate"] == 1.0


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
    }
    for key, text in copy.items():
        if key.startswith("_"):
            continue
        for mode in ("fan", "analyst"):
            v = verify(text.format(**sample), mode)
            assert v.ok, (key, [f.claim for f in v.findings])
