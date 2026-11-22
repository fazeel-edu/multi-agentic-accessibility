---
title: 'Story 2.7: Synthesis Agent'
type: 'feature'
created: '2026-11-21'
status: 'done'
route: 'dispatch'
---

Acceptance criteria: `planning/epics.md` Story 2.7.

## Implementation Notes

- Runs after the six end or fail; role `inclusive_design`, no tools, sees all role outputs and the failed-role list. Gate requires `derived_from` on every issue; `priority_notes` kept on the Run, not as Issues. Failure keeps the six outputs with synthesis `failed`; all six failed skips synthesis (`no_input`).
