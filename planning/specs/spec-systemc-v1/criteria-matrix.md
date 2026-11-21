# Criteria Matrix (draft, Proposal V1.1 section 5.3)

Draft of about 20 criteria; freeze and date before any Evaluation Run. R = rule-checkable, J = judgement-based, M = mixed. Roles are needs or interaction perspectives, not medical labels. Several criteria sit under two Roles on purpose; the orchestrator removes duplicates.

| Criterion | Type | Primary role(s) |
| --- | --- | --- |
| 1.1.1 Non-text Content (A) | M | Screen reader |
| 1.3.1 Info and Relationships (A) | M | Screen reader |
| 1.3.2 Meaningful Sequence (A) | J | Screen reader, Cognitive |
| 1.4.1 Use of Colour (A) | J | Colour and visual |
| 1.4.3 Contrast (Minimum) (AA) | R | Colour and visual |
| 1.4.10 Reflow (AA) | M | Colour and visual |
| 1.4.11 Non-text Contrast (AA) | R | Colour and visual |
| 2.1.1 Keyboard (A) | M | Keyboard |
| 2.1.2 No Keyboard Trap (A) | M | Keyboard |
| 2.4.1 Bypass Blocks (A) | R | Keyboard, Screen reader |
| 2.4.3 Focus Order (A) | J | Keyboard |
| 2.4.4 Link Purpose, In Context (A) | J | Screen reader, Plain language |
| 2.4.6 Headings and Labels (AA) | J | Screen reader, Plain language, Cognitive |
| 2.4.7 Focus Visible (AA) | M | Keyboard |
| 2.4.11 Focus Not Obscured, Minimum (AA) | M | Keyboard, Colour and visual |
| 3.1.1 Language of Page (A) | R | Plain language |
| 3.3.1 Error Identification (A) | M | Cognitive, Plain language |
| 3.3.2 Labels or Instructions (A) | J | Cognitive, Plain language |
| 3.3.3 Error Suggestion (AA) | J | Cognitive, Plain language |
| 3.3.7 Redundant Entry (A) | J | Cognitive |
| 4.1.2 Name, Role, Value (A) | M | Screen reader |

WCAG structure covers structural criteria the user roles do not; it is kept narrow so it does not act as a criterion checker. The matrix lists 21 rows against "about 20" in the proposal; the final list is set in week 3.

## Roles: inputs and tools

| Role | Sees | Tools | Judges |
| --- | --- | --- | --- |
| Screen reader | accessibility tree, headings, landmarks, labels, alt text, reading order | axe-core | whether a screen-reader user can understand and navigate the page |
| Keyboard | focus trace, interactive elements, focus styles | axe-core, focus-trace reader | reachable, in order, visible, no traps |
| Colour and visual | screenshot, computed styles | contrast calculator | contrast, colour-only meaning, reflow, hidden focus |
| Cognitive | layout, instructions, forms, errors | readability scorer | overload, error recovery, redundant entry |
| Plain language | visible text, labels, links, errors | readability scorer | clear wording, link and heading purpose |
| WCAG structure | HTML, ARIA, axe output | axe-core | structural criteria the roles do not cover |
| Inclusive design (synthesis) | whole capture + six role outputs | none | patterns across findings |
