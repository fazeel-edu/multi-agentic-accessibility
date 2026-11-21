---
title: 'Story 1.6: Capture a page'
type: 'feature'
created: '2026-11-21'
status: 'done'
route: 'dispatch'
---

## Intent

Capture a local page once into an immutable Capture every system reads (AD-3, FR5, FR6). Acceptance criteria: `planning/epics.md` Story 1.6.

## Implementation Notes

- Command: `uv run systemc capture <page.html> [--page-id ID]` (`cli/main.py`, script entry `systemc`).
- `capture/capture.py` drives headless Chromium (1280x800, light, reduced motion, remote requests aborted and counted). Artifacts: `page.html` (rendered DOM), `computed_styles.json`, `accessibility_tree.yaml` (Playwright aria snapshot), `axe_results.json`, `focus_trace.json`, `contrast.json`, `screenshot.png`, plus `capture.json`.
- axe-core 4.14.1 is vendored in `vendor/axe-core/`, injected with `eval` after all other artifacts (no DOM change), tags wcag2a, wcag2aa, wcag21a, wcag21aa, wcag22aa. axe `incomplete` is stored as `needs_review`; `timestamp`, `url`, `testEnvironment` are stripped so re-captures hash the same.
- Focus trace: forward Tab pass, reverse Shift+Tab pass from the page bottom (up to 120 steps each), and dialog probes (click each non-submit button, record whether focus moves into a dialog it opens). Each step records the active element, focus indicator and how many of 5 sampled points are covered by another element. Script version recorded.
- `capture_hash` (`contract/capture.py`) covers HTML, accessibility tree, styles, axe results and focus trace; not screenshot, contrast or timestamps. Contract adds `CaptureManifest` and `Capture`.
- `store/captures.py` is the only file writer: stages in a temp dir, renames into `data/captures/{page_id}/{capture_hash}/`, never rewrites an existing Capture, and `read_capture` verifies every artifact hash.
- Style and contrast paths use the same canonical scheme as `tools.element`; a test checks that every path resolves through `element_key`.
- Result on `fixture-01` (hash 4bc8c35f...): axe finds only `color-contrast` on `#shipping-note` (misses T4-T9, including placeholder-only label), contrast row 2.78, forward focus order as expected, dialog probe shows focus stays on the opener and Tab goes behind the dialog (T7 confirmed).
- T8 changed: reverse Tab covers `#more-1`, `#more-2` and `#more-3` by the sticky header (5/5 points), not `#jump-terms`. Draft ground truth now lists those three for T8 (they also carry T2); `#jump-terms` became a control. Depends on this viewport and Chromium build, but ground truth binds to the pinned capture.
- Needs a one-time `uv run playwright install chromium`; browser tests skip if Chromium is absent.
- Code review (2026-11-21): patches applied, see `planning/reviews/epic-1-code-review.md`. Focus trace is now script version 2: `tab_forward_end`/`tab_backward_end` and `dialogs {probes, candidates, probed}` replace `dialog_probes`; `capture` may import `tools.element` to check path parity.
