---
title: 'Story 2.9: Run storage and audit command'
type: 'feature'
created: '2026-11-21'
status: 'review'
route: 'dispatch'
---

Acceptance criteria: `planning/epics.md` Story 2.9.

## Implementation Notes

- `store/runs.py` writes `run.json`, `issues.jsonl`, `tool_calls.jsonl` once (exclusive create) and `report.{version}.json` derived; `read_run` rebuilds the AuditResult. `systemc audit <page_id> [--phase --group-id --exclude --resume --capture-hash]` checks provider terms, prints the cost estimate, runs, stores and post-processes. Run records config hash, SDK/CLI versions, phase, model ID, group_id, provider terms date, per-role status.
- Verified with a fake session on the fixture-01 capture. The first real report needs the API key and filled `config/provider_terms.md`.
