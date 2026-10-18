#!/usr/bin/env sh
# The two demo matches (PLAN decision 21): generate, estimate, and write their feeds, including
# the story match with its left-back as the favourite (decision 25; the site and the video).
# Synthetic data only. Add --offline to skip Foundry (templates and rules, deterministic).
# The committed feeds of the demo are in docs/feeds/ (LLM output differs from run to run), and
# the committed overlay data in app/public/data/ (decision 26): the same seed gives a different
# match on another machine, so regenerate only to replace both together.
set -e
D=data/synthetic/demo
uv run python -m secondwind.sim --seed 2028 --story press-fade --out "$D/story"
uv run python -m secondwind.sim --seed 2031 --out "$D/natural"
for m in story natural; do
    uv run python -m secondwind.engine "$D/$m"
    uv run --extra agents python -m secondwind.agents.feed "$D/$m" "$@"
done
uv run --extra agents python -m secondwind.agents.feed "$D/story" --favourite H04 \
    --out "$D/story/feed_h04.json" "$@"
uv run python -m secondwind.export "$D/story" --out app/public/data/story --feed "$D/story/feed_h04.json"
uv run python -m secondwind.export "$D/natural" --out app/public/data/natural
# For the committed demo feeds instead of fresh ones:
#   uv run python -m secondwind.export $D/story --out app/public/data/story --feed docs/feeds/story_h04.json
#   uv run python -m secondwind.export $D/natural --out app/public/data/natural --feed docs/feeds/natural.json
