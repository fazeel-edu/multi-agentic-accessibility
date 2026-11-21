# Deferred work

## Deferred from: code review of Epic 1 (2026-11-21)

- `issue_id` hashes element_key + criterion + role only: two axe rules on one element with a null criterion collide. Decide when axe rule_ids are mapped (Story 2.8, 3.1).
- Contrast script drops colours that are not `rgb()/rgba()` and ignores ancestor opacity, disabled controls and clipped text. Fine for Seeded Pages; revisit for real pages.
- Dialog probe does not wait for dialogs that open asynchronously, and does not press Escape or check that focus returns to the opener (2.1.2, 2.4.3).
- Capture hash includes element rects and focus geometry, so it depends on fonts and the Chromium build. Same-machine re-capture is stable; cross-machine is not tested. Pin the build (recorded in `docs/pins.md`) and capture once.
- Matrix lacks 2.5.8 Target Size, 4.1.3 Status Messages (the fixture's "Invalid" has no live region), 1.4.4, 1.4.12. Decide at the week-3 matrix freeze.
- `Issue.derived_from` and `Issue.role` are not restricted to synthesis at contract level; enforce at the output gate in Story 2.5/2.7.
- axe `rule_id` to criterion mapping needs a `rule_ids` field on matrix entries (schema change and re-hash): Story 2.8.
- `fixture-01.draft.json` has an ad hoc shape and T8 items derived from the pinned capture; Story 4.2 replaces it with bound ground truth.
- A corrupt existing Capture (tampered artifacts) is returned as is by `write_capture`; `read_capture` detects it. Add a repair path if it ever happens.
