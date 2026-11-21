---
title: 'Story 1.4: T1-T9 fixture page'
type: 'feature'
created: '2026-11-21'
status: 'in-review'
route: 'dispatch'
---

## Intent

Hand-built page reproducing the proposal's T1-T9 defects plus a clean control and a Decoy, with a draft ground-truth table. Acceptance criteria: `planning/epics.md` Story 1.4.

## Implementation Notes

- Page: `data/pages/fixture-01.html` (`page_id` fixture-01; not in the manifest until Story 4.7). No comments or defect-revealing names in the HTML, so agents cannot read the answer.
- Draft ground truth: `data/ground_truth/fixture-01.draft.json`, 15 items: T1 hero alt "image123.png"; T2 five "Click here" links (five items); T3 shipping note at 2.78:1; T4 placeholder-only full name; T5 promo field with red border only; T6 phone message "Invalid"; T7 size-guide dialog that never moves focus; T8 `#jump-terms` link (reverse tab lands under the sticky header); T9 three vague headings (Info, More, Stuff). Also `no_issue_criteria`, `controls`, `decoys`. Selectors only; Story 4.2 binds them to element keys.
- Control: labelled email field, described photo, "Delivery options" heading, other links. Decoys: aria-hidden SVG icon beside a text button, empty-alt divider image.
- T7 and T8 are interaction defects: the dialog is hidden until opened, and the header obscuring needs a scroll plus reverse Tab. I did not confirm either in a browser (installed Chromium does not match Playwright 1.65.2). Confirm when Story 1.6 captures the page.
- Draft until Fazeel reviews: contrast value, severities, expected roles, acceptable alternative criteria (T4: 3.3.2/1.3.1/4.1.2; T5: 1.4.1/3.3.1; T6: 3.3.3/3.3.1).
- `tests/test_fixture_page.py` checks defects present, selectors unique, enums and criteria valid against the contract and Config matrix, and no leaked labels.
