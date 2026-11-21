---
title: 'Story 1.2: Shared contract models and exported schema'
type: 'feature'
created: '2026-11-21'
status: 'in-review'
route: 'dispatch'
---

## Intent

One set of pydantic contract models (AD-2) shared by agents, post-processing, scoring and review. Acceptance criteria: `planning/epics.md` Story 1.2.

## Implementation Notes

- `contract/enums.py`: `Role` (8, closed), `Severity` (IntEnum 1-4 MINOR..CRITICAL), `IssueType`, `Scope`, `Phase`, `System`, `RoleState`, `RunState`.
- `contract/models.py`: `Issue` is the agent/adapter shape with `extra="forbid"`, so code-set fields (confidence, severity, rank, grounded, roles, element_key, id) are rejected. `KeyedIssue` adds `element_key` and `id`. `MergedIssue` holds all code-set fields. Also `AgentOutput`, `AuditResult`, `GroundTruthItem`, `PageGroundTruth` (carries `no_issue_criteria`), `Run`, `Report`.
- `contract/element_key.py`: discriminated union `node | nodes | page | unresolved`, frozen and hashable. Parsing stays in `tools.element` (Story 1.5).
- `schema_version` ("1") on every top-level model; not on embedded value types (keys, `FailureRecord`, `RoleStatus`, `Usage`, `ToolCall`).
- Evidence is non-empty at model level; `criterion` must match `N.N.N`.
- `issue_v1.json` (plus ground truth, run, report schemas) exported to `contract/schemas/` by `scripts/export_schemas.py`; a test fails if the committed files drift from the models.
- Decisions made by me, open to change: severity names and 1-4 scale (the numeric rank rule stays deferred to `postprocess/rank.py`); `Issue.criterion` nullable (axe emits `rule_id`).
