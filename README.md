# SystemC_V1

Role-based multi-agent accessibility audit (System C) compared with an axe-core baseline (System A) on synthetic Seeded Pages. Architecture: `planning/architecture/architecture-SystemC_V1-2026-11-21/ARCHITECTURE-SPINE.md`.

## Setup

```
uv sync
uv run playwright install chromium   # once; Capture and browser tests need it
git config core.hooksPath .githooks   # secret-blocking pre-commit
uv run pytest                        # REQUIRE_BROWSER=1 makes a missing Chromium fail, not skip
uv run ruff check .
```

`ANTHROPIC_API_KEY` is read from the environment only. Never put it in a file.

Pinned versions and verification date: `docs/pins.md`.

## Commands

```
uv run systemc capture data/pages/fixture-01.html   # writes data/captures/{page_id}/{capture_hash}/
```

## System C audit (Epic 2)

```
cp .env.systemc.example .env.systemc   # put your key in it (git-ignored; not exported to your shell or Claude Code)
# fill in config/provider_terms.md (Read on: YYYY-MM-DD plus three topics)
uv run systemc capture data/pages/fixture-01.html
uv run systemc audit fixture-01      # prints a cost estimate, runs 6 roles + synthesis, stores the Run
uv run pytest tests/test_sdk_live.py -s   # Story 2.1 live checks (paid, small)
```

After a Cost Cap stop the next `systemc audit` in that phase refuses until you raise `cost_cap_usd` in `config/settings.toml` and pass `--resume`.
