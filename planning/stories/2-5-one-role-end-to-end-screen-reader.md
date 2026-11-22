---
title: 'Story 2.5: One role end to end'
type: 'feature'
created: '2026-11-21'
status: 'done'
route: 'dispatch'
---

Acceptance criteria: `planning/epics.md` Story 2.5.

## Implementation Notes

- Role Specs are `config/roles/{role}.json` (validated by `contract/role_spec.py`, loaded by `store/roles.py`); screen_reader has 3 examples taken from fixture-01 (placeholder source until Story 6.1).
- `role_runner.run_agent`: isolated session via the `SessionRunner` port, output gate (`parse_output`), one retry then `failed` with `{stage, kind, message, retryable}`, prompt-size estimate and example count in `RoleStatus`, tool calls hook-logged. `sdk_runner.SdkSessionRunner` sets `setting_sources=[]`, `tools=[]`, built-ins disallowed, empty temp cwd.
- Tested against a scripted fake session; the real SDK path is untested until Story 2.1 runs live.
