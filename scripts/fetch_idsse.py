"""Download the IDSSE dataset [Bassek2025] (CC BY 4.0) into data/raw/idsse/.

Calibration only: the raw files are git-ignored and never redistributed (PLAN §2.2).
File ids are figshare's (doi:10.6084/m9.figshare.28196177), as listed in floodlight's
IDSSEDataset. Read the files with ``floodlight.io.dfl``.

Usage: uv run python scripts/fetch_idsse.py [MATCH_ID ...]   (default: all 7 matches, ~2.4 GB)
"""

import sys
import urllib.request
from pathlib import Path

FIGSHARE = "https://ndownloader.figshare.com/files/{}"
# match id: (info, events, positions)
FILES = {
    "J03WMX": ("51643475", "51643493", "51643514"),
    "J03WN1": ("51643472", "51643496", "51643517"),
    "J03WPY": ("51643487", "51643505", "51643526"),
    "J03WOH": ("51643478", "51643499", "51643520"),
    "J03WQQ": ("51643484", "51643508", "51643529"),
    "J03WOY": ("51643481", "51643502", "51643523"),
    "J03WR9": ("51643490", "51643511", "51643532"),
}
KINDS = ("info", "events", "positions")
OUT = Path(__file__).resolve().parents[1] / "data" / "raw" / "idsse"


def fetch(match_id: str) -> None:
    folder = OUT / match_id
    folder.mkdir(parents=True, exist_ok=True)
    for kind, file_id in zip(KINDS, FILES[match_id], strict=True):
        path = folder / f"{kind}.xml"
        if path.exists() and path.stat().st_size > 0:
            print(f"{match_id} {kind}: already there")
            continue
        tmp = path.with_suffix(".part")
        urllib.request.urlretrieve(FIGSHARE.format(file_id), tmp)
        tmp.rename(path)
        print(f"{match_id} {kind}: {path.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    for match_id in sys.argv[1:] or FILES:
        fetch(match_id)
