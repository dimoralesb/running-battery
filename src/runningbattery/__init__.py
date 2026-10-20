"""Running Battery: hard running from football tracking data, and what it would leave a typical
professional."""

__version__ = "0.1.0"

import os


def default_workers() -> int:
    """Worker processes for batch runs: one per physical core (half the logical CPUs, assuming
    two hardware threads per core). On a 16-core Ryzen 9 7950X, 32 workers were only 3% faster
    than 16 (64 matches, 2026-10-17), so the second hardware thread is left free."""
    return max(1, (os.cpu_count() or 2) // 2)
