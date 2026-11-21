---
title: 'Story 2.1: SDK smoke tests'
type: 'feature'
created: '2026-11-21'
status: 'in-progress'
route: 'dispatch'
---

Acceptance criteria: `planning/epics.md` Story 2.1.

## Implementation Notes

- `tests/test_sdk_live.py` (skipped without `ANTHROPIC_API_KEY`) checks the allowlist hook allows one tool and denies another, and that built-ins are unavailable. `auditors/role_auditor/hook.py` is the hook; `sdk_runner.py` registers it with `on_failure="block"`.
- NOT YET RUN LIVE. Still open until run: the raising-hook-blocks case, whether `task_budget` changes behaviour, whether `ToolSearch` needs allowlisting (it is in the disallowed built-ins list). Record results in the architecture memlog.
