# Glossary

Terms are used verbatim across the spec, spine and PRD.

- **Page / Page Set / Seeded Page / Decoy** — a page evaluated by id; V1 Page Set is Seeded Pages only (LLM-generated, hand-reviewed, planted defects, clean controls, decoys such as a decorative icon correctly hidden). Split into **Dev Set** (tuning, Guidance, Worked Examples) and **Test Set** (scored only).
- **Page Type** — e-commerce, government and public service, forms, content and news (mobile-sized variant optional).
- **Capture** — immutable saved artifacts for one page; **Focus Trace** — scripted keyboard focus sequence, same steps every page.
- **Criterion / Criteria Matrix** — in-scope WCAG 2.2 AA success criteria (about 20) with type R (rule-checkable), J (judgement), M (mixed) and primary Roles; frozen and dated before any Evaluation Run.
- **Role / Role Spec / Role Agent** — user perspective (screen reader, keyboard, colour and visual, cognitive, plain language, WCAG structure); one versioned file of six parts (prompt, criteria subset, inputs, tool allowlist, output schema, examples); the agent run from it.
- **Guidance / Worked Example** — per-Role inspection notes; 3-4 Dev Set cases (clear issue, clean case, borderline).
- **Synthesis Agent** — inclusive-design agent reading the whole Capture and all six outputs; no tools.
- **Orchestrator** — deterministic Python that runs the fixed role table, hooks, validation and post-processing.
- **System A / System C** — axe-core baseline / Orchestrator + six Role Agents + Synthesis Agent. System B (single agent) is deferred.
- **Issue / Confidence** — one reported problem in the shared contract; Confidence is the count of distinct Roles reporting the same element and criterion (1-6), set by code.
- **Ground Truth / Acceptable Criteria / Match** — versioned true-issue list, one item per affected element; criteria any of which count; a report matches on same element and any acceptable criterion. TP/FP/FN count each item once.
- **Grounded** — cited element exists in the Capture.
- **Run / Evaluation Run / Report** — one system on one page; final set after Prompt Freeze (A once, C three times per page); ranked de-duplicated output.
- **Review Screen / Reviewer** — local screen to mark Issues; Fazeel in V1.
- **Config / Cost Cap / Prompt Freeze** — hashed settings; hard spend limit; tagged repo state blocking changes before the Evaluation Run.
- **H1** — hypothesis: C has higher recall than axe-core and than a single agent, precision within 10 points of the single agent, gain largest on judgement-based criteria. Reported, not a gate; V1 tests only the axe-core half.
