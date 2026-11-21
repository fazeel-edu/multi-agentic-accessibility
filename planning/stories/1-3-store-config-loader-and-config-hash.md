---
title: 'Story 1.3: Store, Config loader and Config hash'
type: 'feature'
created: '2026-11-21'
status: 'in-review'
route: 'dispatch'
---

## Intent

One module reads the `config/` folder into a validated Config and hashes the whole folder (FR31, AD-7). Acceptance criteria: `planning/epics.md` Story 1.3.

## Implementation Notes

- `store/config.py`: `load(config_dir=CONFIG_DIR) -> LoadedConfig(config, config_hash)`; `config_hash()` is SHA-256 over sorted relative paths and file bytes of every file in the folder, ignoring `__init__.py`, `.DS_Store` and `__pycache__`.
- `config/settings.toml`: thinking `adaptive`, `max_turns`, per-session `max_budget_usd`, `cost_cap_usd`, dev (Haiku 5.5, effort medium) and eval (Sonnet 5.5, effort high) models.
- `config/criteria_matrix.json`: 21 criteria generated from the draft matrix (status `draft`, `frozen_on` null until Story 6.1).
- Models use `extra="forbid"`, so `temperature`, `top_p`, `max_tokens` and typos are rejected with `ConfigError` (added to `contract/errors.py`).
- `tests/test_store_owns_file_io.py` fails if any package other than `store` calls `open`/`read_text`/`write_text`/etc.
- Decisions made by me, open to change: `max_turns = 12`, `max_budget_usd = 1.0`, `cost_cap_usd = 50.0` (SPEC's unconfirmed figure) and efforts are drafts; the Cost Cap stays an open item until live pricing is checked. `paths.py` holds the data/results/config locations for later store modules.
