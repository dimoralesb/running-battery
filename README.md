# Second Wind

> The story the scoreline doesn't tell: who's running on empty, and when it costs them.

Second Wind estimates football player fatigue from tracking data and explains it to fans and analysts through AI agents on Microsoft Foundry. It is an entry for the Microsoft x Premier League "Inside the Game" hackathon.

All match data is **synthetic**: we built a generator whose players get tired according to published sports science, with a hidden "true" fatigue we use to test our estimator.

**Status:** in development (October 2026).

- Project plan: [docs/PLAN.md](docs/PLAN.md)
- Build plan: [docs/BUILD_PLAN.md](docs/BUILD_PLAN.md)
- Evidence base (64 papers): [docs/RESEARCH_SYNTHESIS.md](docs/RESEARCH_SYNTHESIS.md)
- Data format: [src/secondwind/schema.py](src/secondwind/schema.py), JSON Schemas in [schemas/](schemas/)

## Development

```bash
uv sync                          # Python 3.12 environment
uv run pytest                    # tests
uv run ruff check . && uv run ruff format --check .
uv run python -m secondwind.schema   # re-export JSON Schemas after changing the models
```

## License

MIT. See [LICENSE](LICENSE).
