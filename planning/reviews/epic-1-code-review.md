# Code review: Epic 1 (stories 1.1-1.6)

Date 2026-11-21. Diff: commits aa3c33b..83d6cf8, code, config, tests, docs, fixture only (2,797 lines). Layers: Blind Hunter, Edge Case Hunter, Verification Gap, Acceptance Auditor (spec: `planning/epics.md` Epic 1 and the architecture spine). All four layers reported.

Result: 2 decision-needed (resolved), 12 patch, 10 defer, 14 rejected. All patches applied in the follow-up commit.

## Decisions
- Issues with no criterion after mapping go to `Report.unmapped_issues` (kept for review, excluded from matching, ranking, Confidence). Added to the contract; Story 2.8 criteria updated.
- Matrix: `wcag_structure` gets criteria (1.3.1, 2.4.1, 2.4.2 new, 3.1.1, 4.1.2); 1.4.10 Reflow removed (one viewport only).

## Patched
1. `page_id` and `capture_hash` validated (pattern) in contract, store, capture and CLI; paths cannot leave `data/captures`.
2. Pre-commit hook: NUL-separated names, scans the staged blob, fails closed on read errors, generic `sk-` pattern widened and tested.
3. Focus trace records `tab_forward_end` / `tab_backward_end` (`left_document`, `revisit`, `cap`); script version 2.
4. A button that navigates no longer aborts the capture; probe records `click_failed`; opener cap recorded (`candidates` vs `probed`).
5. Focus trace never stores typed values (only labels of button-like inputs).
6. `file:` requests allowed only under the page's own folder.
7. Capture fails if any browser-side element path does not resolve through `tools.element` (capture may import `tools.element`: one spine deviation, noted in the dependency test).
8. Playwright and OS errors become `CaptureError`; CLI warns when requests were blocked; CLI tests added; axe version guard and vendored header tested.
9. Config: frozen needs a date, `cost_cap_usd >= max_budget_usd`, no inf/nan, bad UTF-8 and hash read errors become `ConfigError`; hash ignores only the top-level `__init__.py`.
10. `element_key`: XPath without a leading slash (`descendant::a`) works; lone surrogates and other lxml errors return `unresolved`.
11. Store: a finished Capture is never deleted by a same-hash race; staging folders are not listed; manifest artifact set checked.
12. `Criterion` type shared from contract; `capture_hash` hex pattern; `REQUIRE_BROWSER=1` turns a missing Chromium into a failure.

## Rejected
- "Files missing from the diff" (schemas, vendor, uv.lock, five `__init__.py`): false, all tracked in git; they were left out of the review diff.
- "`import tools` then attribute access evades the dependency test": false, the checker flags the import itself.
- Generic top-level package names (spine names), embedded types without `schema_version` (documented), `.gitignore` of captures (by design), ruff rule selection, SDK/FastAPI deps listed early, README wording, duplicate timestamp strings, `PARSER` constant unused, cli looser than spine graph (documented), file-I/O test names only (accepted), config stray-file allow-list, `derived_from` only checked later.

## Deferred (see `planning/deferred-work.md`)
`issue_id` collision when criterion is null; contrast ignores non-rgb colours and opacity; asynchronous dialogs; cross-machine hash portability (fonts, rects); more WCAG 2.2 criteria (2.5.8, 4.1.3, 1.4.4, 1.4.12); `derived_from`/`role` gating (Story 2.5); axe `rule_id` to criterion mapping (Story 2.8); Escape and focus-return dialog probing; T8 ground truth derived from the capture and ad hoc draft shape (Story 4.2); repair of a corrupt existing Capture.
