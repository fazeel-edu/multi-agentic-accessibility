---
title: 'Story 2.2: Analysis tools over a Capture'
type: 'feature'
created: '2026-11-21'
status: 'done'
route: 'dispatch'
---

Acceptance criteria: `planning/epics.md` Story 2.2.

## Implementation Notes

- Pure tools in `tools/`: `contrast.py` (calculator, WCAG 1.4.3 check, failing rows from the Capture), `readability.py` (Flesch ease and grade), `focus_trace.py` (summary of order, covered or missing focus, dialogs), `axe_reader.py` (violations, needs-review), `element.element_text`. They read stored artifacts only; a test forbids network use.
- `tools/registry.py`: one `ToolSpec` per tool (name, JSON schema, run function), no SDK import.
- `auditors/role_auditor/tool_table.py`: fixed Role to tools table (least tools, Synthesis and axe have none) and `mcp__a11y__{tool}` names. `sdk_tools.py`: `role_tools` and `build_role_server` make one in-process SDK MCP server per Role holding only that Role's tools; bad arguments return `is_error`.
- Tests run on the real fixture-01 Capture (session fixture in `tests/conftest.py`): contrast 2.78:1 is reported, axe finds only color-contrast, the trace shows T7 and T8.
- Whether the SDK actually applies the allowlist hook to these tools is Story 2.1 (needs the API key).
