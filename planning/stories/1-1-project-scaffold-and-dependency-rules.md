---
title: 'Story 1.1: Project scaffold and dependency rules'
type: 'chore'
created: '2026-11-21'
status: 'in-review'
route: 'dispatch'
review_loop_iteration: 0
context:
  - 'CODEBASE/SystemC_V1/planning/architecture/architecture-SystemC_V1-2026-11-21/ARCHITECTURE-SPINE.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** No code project exists. Later stories need a place that enforces the spine's package layout and dependency graph.

**Approach:** uv Python 3.12 package with the eleven spine packages, an import-graph test, `.gitignore`, a secret-blocking pre-commit hook, and recorded pins. Repo: git init in `CODEBASE/SystemC_V1`, remote `https://github.com/fazeel-edu/multi-agentic-accessibility`, branch `main` (user authorised pushing; remote was empty).

## Boundaries & Constraints

**Always:** package names exactly `config, contract, capture, tools, auditors, postprocess, eval, store, review, cli, tools_dev`; dependency edges only as in the spine graph; Python 3.12; pins verified against PyPI 2026-11-21.

**Never:** feature code beyond empty packages; committing `.env`, `results/`, `data/captures/`; real API keys anywhere.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected | Error Handling |
|---|---|---|---|
| Allowed import | `cli` imports `eval` | test passes | N/A |
| Forbidden import | `eval` imports `auditors` | test fails | names offending edge |
| Key-shaped string | staged file has `sk-ant-...` | hook exits 1 | prints file |

</frozen-after-approval>

## Code Map

- Spine graph: ARCHITECTURE-SPINE.md "Invariants & Rules" (edges); `postprocess`/`eval` may import only `tools.element` from `tools`.

## Tasks & Acceptance

**Execution:**
- [ ] `pyproject.toml`, `.python-version` -- uv project, pinned deps, pytest/ruff config
- [ ] one `__init__.py` per package -- layout
- [ ] `tests/test_dependency_rules.py` -- AST-based import graph check, plus self-test of the checker
- [ ] `.gitignore`, `scripts/check_secrets.py`, `.githooks/pre-commit`, `tests/test_check_secrets.py` -- AD-16
- [ ] `docs/pins.md`, `README.md` -- recorded pins and setup

**Acceptance Criteria:**
- Given a clean checkout, when `uv sync && uv run pytest`, then tests pass and all eleven packages import.
- Given a forbidden import, when the dependency test runs, then it fails.

## Implementation Notes

## Verification

**Commands:**
- `uv run pytest` -- expected: all pass
- `uv run ruff check .` -- expected: clean
