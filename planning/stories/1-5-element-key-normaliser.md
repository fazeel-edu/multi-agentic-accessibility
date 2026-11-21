---
title: 'Story 1.5: element_key normaliser'
type: 'feature'
created: '2026-11-21'
status: 'done'
route: 'dispatch'
---

## Intent

One function turns a CSS selector or XPath into a canonical element key (AD-15). Acceptance criteria: `planning/epics.md` Story 1.5.

## Implementation Notes

- `tools/element.py`: `element_key(capture_html, selector) -> ElementKey`. Parser: lxml.html (libxml2), comments and PIs removed; CSS goes through cssselect to XPath. Canonical path is `/html[1]/body[1]/...` with a 1-based same-tag index at each level. Pins: lxml 6.1.3, cssselect 1.6.0 (`pyproject.toml`, `docs/pins.md`).
- Result kinds: one match is `node`, several are `nodes` (document order, de-duplicated), `None` selector is `page`, no match or invalid syntax or non-node XPath result is `unresolved`. Never raises on bad selectors.
- Selector is XPath when it starts with `/`, `(`, `./`, `../`; otherwise CSS.
- XPath attribute and text results (`//img/@alt`) map to the owning element.
- Parsed documents are cached (`lru_cache`, 8) so many calls on one Capture parse once.
- Keys are those of libxml2's HTML parser, not a browser's DOM (for example no implied `tbody`). All systems and ground truth use the same function, so keys stay comparable; if Captures later store rendered DOM HTML the two will agree more often.
- Tests (`tests/test_element_key.py`): CSS vs XPath vs absolute path give equal keys, unresolved cases, all 15 fixture ground-truth selectors resolve to distinct nodes.
