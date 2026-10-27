"""The pitch text for the submission form (docs/PITCH.md) passes the Verifier's rules, sentence
by sentence, as the overlay's fixed copy does."""

import re
from pathlib import Path

import pytest

from runningbattery.agents.verifier import verify

PITCH = Path(__file__).resolve().parents[1] / "docs" / "PITCH.md"
# The pitch is kept out of the public repository; the test runs where the file is.
pytestmark = pytest.mark.skipif(not PITCH.exists(), reason="docs/PITCH.md is not in this checkout")


def sentences() -> list[str]:
    """The sentences of the two versions (not the intro or the sources table)."""
    text = PITCH.read_text().split("## Sources")[0].split("## Short version", 1)[1]
    text = re.sub(r"^#.*$|\*\*[^*]+\*\*|https?://\S+", " ", text, flags=re.M)
    text = " ".join(text.split())
    return [s for s in re.split(r"(?<=[.!?])\s+(?=[A-Z])", text) if len(s) > 3]


def test_pitch_passes_the_verifier():
    found = sentences()
    assert len(found) >= 20
    for mode in ("fan", "analyst"):
        for s in found:
            v = verify(s, mode)
            assert v.ok, (s, [f.claim for f in v.findings])
