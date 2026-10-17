#!/usr/bin/env sh
# The two demo matches (PLAN decision 21): generate, estimate, and write their feeds.
# Synthetic data only. Add --offline to skip Foundry (templates and rules, deterministic).
# The committed feeds of the demo are in docs/feeds/ (LLM output differs from run to run).
set -e
D=data/synthetic/demo
uv run python -m secondwind.sim --seed 2028 --story press-fade --out "$D/story"
uv run python -m secondwind.sim --seed 2031 --out "$D/natural"
for m in story natural; do
    uv run python -m secondwind.engine "$D/$m"
    uv run --extra agents python -m secondwind.agents.feed "$D/$m" "$@"
done
