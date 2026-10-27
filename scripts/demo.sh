#!/usr/bin/env sh
# The two demo matches: generate, estimate, and write their feeds (no
# favourite player since then: each feed describes its match's most relevant moments).
# Synthetic data only. Add --offline to skip Foundry (templates and rules, deterministic).
# The committed feeds of the demo are in docs/feeds/ (LLM output differs from run to run), and
# the committed overlay data in app/public/data/: the same seed gives a different
# match on another machine, so regenerate only to replace both together.
set -e
D=data/synthetic/demo
uv run python -m runningbattery.sim --seed 2028 --story press-fade --out "$D/story"
uv run python -m runningbattery.sim --seed 2031 --out "$D/natural"
for m in story natural; do
    uv run python -m runningbattery.engine "$D/$m"
    uv run --extra agents python -m runningbattery.agents.feed "$D/$m" "$@"
done
uv run python -m runningbattery.export "$D/story" --out app/public/data/story
uv run python -m runningbattery.export "$D/natural" --out app/public/data/natural
# For the committed demo feeds instead of fresh ones:
#   uv run python -m runningbattery.export $D/story --out app/public/data/story --feed docs/feeds/story.json
#   uv run python -m runningbattery.export $D/natural --out app/public/data/natural --feed docs/feeds/natural.json
