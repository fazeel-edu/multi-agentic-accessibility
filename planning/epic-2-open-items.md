# Epic 2 open items (2026-11-22)

Stories 2.2-2.9 are done and reviewed (`planning/reviews/epic-2-code-review.md`). Story 2.1 stays in progress.

To finish Story 2.1 and prove the real SDK path:
1. Fill in `config/provider_terms.md` (read the provider terms yourself; date it).
2. Put the Console API key in `.env.systemc` (copy `.env.systemc.example`).
3. `uv run pytest tests/test_sdk_live.py -s` (small paid test).
4. Record in the architecture memlog: does a raising hook block the call, does `task_budget` change behaviour, does `ToolSearch` need allowlisting.
5. `uv run systemc capture data/pages/fixture-01.html` then `uv run systemc audit fixture-01`; read the Report.

After a Cost Cap stop, the next audit in that phase refuses until you raise `cost_cap_usd` in `config/settings.toml` and pass `--resume`.
