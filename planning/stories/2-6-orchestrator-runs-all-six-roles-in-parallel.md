---
title: 'Story 2.6: Orchestrator'
type: 'feature'
created: '2026-11-21'
status: 'review'
route: 'dispatch'
---

Acceptance criteria: `planning/epics.md` Story 2.6.

## Implementation Notes

- `orchestrator.audit`: fixed `ROLES` table, `asyncio.gather`, per-role and per-Run seconds, `exclude` set (ablation) recorded as `Run.variant`, excluded roles reported as `excluded`. Provider errors retried twice with backoff (1s, 3s); timeout and non-retryable errors fail only that role. Each attempt reserves and settles in the ledger.
- Tests: exactly one session per role, parallelism (6 in flight), failed role does not sink the Run, no role sees another's output.
