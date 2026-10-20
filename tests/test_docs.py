"""Docs: every citation key in the README is in docs/References.bib (BUILD_PLAN "Sun 25")."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# A citation key: a name and a year, maybe a letter ("Allen2026a", "SilvaH2025", "IFAB2025").
KEY = r"\b([A-Za-z]+\d{4}[a-z]?)\b"


def bib_entries() -> list[tuple[str, str]]:
    text = (ROOT / "docs" / "References.bib").read_text()
    return re.findall(r"@\w+\{([^,\s]+),(.*?)\n\}", text, re.S)


def resolves(key: str, entries: list[tuple[str, str]]) -> bool:
    """Through the entry's "Cited as" note, or its BibTeX key: the first author's surname (the
    citation key without its initials, e.g. SilvaH, SilvaJR) at the start and the year at the
    end."""
    if any(re.search(rf"Cited as {key}\b", body) for _, body in entries):
        return True
    m = re.fullmatch(r"(.+?)(?:[A-Z]{1,2})?(\d{4})[a-z]?", key)
    name, year = m.group(1).lower(), m.group(2)
    return any(
        re.sub(r"[^a-z]", "", bib.lower()).startswith(name) and bib.endswith(year)
        for bib, _ in entries
    )


def cited(text: str) -> set[str]:
    """Keys inside square brackets ("[Leifsson2024, Table 1; Ju2022]")."""
    return {k for group in re.findall(r"\[([^\]]+)\]", text) for k in re.findall(KEY, group)}


def test_claims_register_sources_are_in_the_bib():
    """The feed shows each claim's sources on screen."""
    import json

    reg = json.loads((ROOT / "src" / "runningbattery" / "agents" / "claims.json").read_text())
    entries = bib_entries()
    keys = {k for c in reg["claims"] for k in c.get("sources") or []}
    missing = sorted(k for k in keys if not resolves(k, entries))
    assert not missing, missing


def test_readme_citations_are_in_the_bib():
    keys = cited((ROOT / "README.md").read_text())
    assert len(keys) >= 20
    entries = bib_entries()
    missing = sorted(k for k in keys if not resolves(k, entries))
    assert not missing, missing
