---
title: 'Story 2.8: Post-processing to a Report'
type: 'feature'
created: '2026-11-21'
status: 'done'
route: 'dispatch'
---

Acceptance criteria: `planning/epics.md` Story 2.8.

## Implementation Notes

- `postprocess.run(audit_result, capture, matrix, run_meta) -> Report` (pure): `mapping.py` resolves element keys and assigns criteria (reporter's criterion kept only if in the matrix; `rule_id` expands through matrix `rule_ids`, one rule may yield several criteria), `dedupe.py` merges on (element key, criterion), voters exclude `inclusive_design` echoes (synthesis-only groups keep one voice), Confidence = distinct roles, `rank.py` holds the documented severity and rank rule.
- Matrix model moved to `contract/matrix.py`; entries gained `severity` (CRITICAL for 2.1.1/2.1.2, SERIOUS for other level A, MODERATE for AA) and `rule_ids` (built from axe-core 4.14.1 tags by `scripts/build_axe_rule_map.py`). Config hash changed.
- Issues with no criterion go to `Report.unmapped_issues` (distinct by element, criterion, role and rule). `grounded` is true for node and nodes keys only.
- Rank: severity, confidence, type (R, M, J), criterion, element key. Order of input never changes the Report (tested by shuffling).
- `cannot_test_statement` is a fixed text in `postprocess/pipeline.py`; `POSTPROCESS_VERSION = "1"`.
