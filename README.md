# SystemC_V1

Role-based multi-agent accessibility audit (System C) compared with an axe-core baseline (System A) on synthetic Seeded Pages. Architecture: `planning/architecture/architecture-SystemC_V1-2026-11-21/ARCHITECTURE-SPINE.md`.

## Setup

```
uv sync
uv run playwright install chromium   # once; Capture and browser tests need it
git config core.hooksPath .githooks   # secret-blocking pre-commit
uv run pytest
uv run ruff check .
```

`ANTHROPIC_API_KEY` is read from the environment only. Never put it in a file.

Pinned versions and verification date: `docs/pins.md`.

## Commands

```
uv run systemc capture data/pages/fixture-01.html   # writes data/captures/{page_id}/{capture_hash}/
```
