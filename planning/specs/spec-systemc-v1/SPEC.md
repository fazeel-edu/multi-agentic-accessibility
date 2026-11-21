---
id: SPEC-systemc-v1
companions:
  - ../../architecture/architecture-SystemC_V1-2026-11-21/ARCHITECTURE-SPINE.md
  - ../../prds/prd-SystemC_V1-2026-11-08/addendum.md
  - glossary.md
  - criteria-matrix.md
sources:
  - ../../prds/prd-SystemC_V1-2026-11-08/prd.md
  - ../../briefs/brief-SystemC_V1-2026-11-08/brief.md
---

> **Canonical contract.** This SPEC and the files in `companions:` are the complete, preservation-validated contract for what to build, test, and validate. Source documents listed in frontmatter are for traceability — consult them only if you need narrative rationale or prose color this contract intentionally omits.

# SystemC_V1

## Why

A mandate and an opportunity for an MSc dissertation (Proposal V1.1). Rule engines such as axe-core test web accessibility fast but cover only part of WCAG 2.2; many barriers need judgement. A recent criterion-split LLM auditor (Mishra et al., 2026) reached 86% recall at 56% precision, and nobody has tested a split by user role. Fazeel needs a working, reproducible pipeline and first honest numbers in one week, to de-risk agent design, harness, cost and run-to-run variance before the formal 25-30 page, expert-checked evaluation. A null result is a valid outcome.

## Capabilities

- **CAP-1**
  - **intent:** Fazeel can build a synthetic Page Set (about 8-10 LLM-generated, hand-reviewed Seeded Pages across e-commerce, government and public service, forms, and content and news) with ground truth written before any system runs.
  - **success:** Every page is in the manifest with Page Type, Dev/Test flag, generator model and `reviewed` status; every planted defect has a ground-truth item (element, acceptable criteria, user group, severity, R/J/M type); per-page criteria with no issue are recorded; at least one defect per Role, clean controls and decoys exist; one page reproduces the T1-T9 example; ground truth is committed before any Run for that page.

- **CAP-2**
  - **intent:** The system can capture a page once into an immutable, cached Capture that every system reads.
  - **success:** A Seeded Page capture contains HTML, computed styles, accessibility tree, screenshot, scripted focus trace, axe results and contrast measurements; a second Run makes zero requests to the page origin; the manifest pins one `capture_hash` per page.

- **CAP-3**
  - **intent:** System A can audit a Capture with axe-core (WCAG 2.2 AA tags) and emit Issues in the shared contract.
  - **success:** Two Runs on one Capture give identical Issues; "needs review" results are stored apart and excluded from precision and recall; A recovers at least 90% of planted rule-checkable defects on Seeded Pages.

- **CAP-4**
  - **intent:** System C can audit a Capture with six isolated Role Agents in parallel, then a Synthesis Agent, driven by deterministic code.
  - **success:** Each Run calls every Role exactly once from a fixed table; each Role gets only its Role Spec inputs, criteria subset, Guidance and 3-4 Dev Set Worked Examples; off-allowlist tool calls are denied and logged; invalid or evidence-free output is retried once then the role is marked failed while others continue; the Synthesis Agent has no tools and runs after all six end or fail.

- **CAP-5**
  - **intent:** Raw Issues from any system can become a deterministic, ranked, WCAG-mapped Report.
  - **success:** Duplicates merge on (element, criterion) with the reporting Roles listed; Confidence equals the count of distinct Roles; each Issue has a criterion, severity, rank and grounded flag; the Report carries a "what the system cannot test" statement; the ranking rule is unit-tested.

- **CAP-6**
  - **intent:** The harness can score any Report against ground truth with one matching rule and report precision, recall and F1.
  - **success:** A report matches a ground-truth item when it names the same element and any acceptable criterion; each item counts once and repeated problems count per element; unit tests cover exact, acceptable-alternative, wrong criterion, wrong element, duplicates and selector-versus-XPath; the T1-T9 fixture yields expected TP/FP/FN; metrics come per system, issue type and Page Type, and for C per Role.

- **CAP-7**
  - **intent:** The harness can report quality, cost and behaviour measures beyond P/R/F1.
  - **success:** Reported for A and C: precision at top 10 and Spearman rank vs ground-truth severity; WCAG coverage of criterion-page pairs; for C: precision by Confidence (1, 2, 3+ Roles), per-Role recall and unique contribution, Synthesis-only issues, schema-valid, evidence-present, grounding and retry rates, run-to-run agreement over 3 Runs, calls, tokens, seconds and estimated USD per Page, cost per true positive; a role-removal ablation (including removing the Synthesis Agent) runs if time allows.

- **CAP-8**
  - **intent:** Fazeel can reproduce the comparison table and results note from stored files.
  - **success:** One command writes the A-vs-C metrics table as Markdown and CSV from JSONL with zero API calls; a results note reports against hypothesis H1, lists at least three lessons for dissertation weeks 3-10, and states the synthetic-page and no-System-B limits.

- **CAP-9**
  - **intent:** The Reviewer (Fazeel) can read a Report and mark each Issue accepted, rejected or unsure.
  - **success:** The screen lists ranked Issues with element, criterion, Roles, evidence, description, fix, Confidence and a grounded flag; decisions are appended beside the Report; an ungrounded Issue cannot be accepted without an override note; every screen states the output is guidance, not a compliance certificate.

- **CAP-10**
  - **intent:** Fazeel can run each stage reproducibly and within budget.
  - **success:** Config (model, effort, loop cap, per-session budget, prompts, matrix) is hashed and stored per Run; a cost estimate prints before LLM Runs and the Run stops cleanly at the Cost Cap; dev iteration uses the dev model on Dev pages only; the Evaluation Run refuses to start if the Prompt Freeze tag, config hash, model ID or dated provider-terms record check fails; capture, each system, evaluation and the review screen start from one documented command each.

## Constraints

- System C's orchestrator is deterministic code with a fixed role table; no LLM routes or skips roles.
- Role Agents share no context, are read-only, and hold only their assigned tools, enforced by a fail-closed hook; the Synthesis Agent has no tools.
- Agents never set confidence, severity, rank or criterion mapping; post-processing code does, identically for every system.
- Final runs use `claude-sonnet-5-5` for every Role and synthesis; `claude-haiku-5-5` for dev on Dev pages only; never mixed in one final comparison.
- The Claude Agent SDK cannot set temperature, top_p or max_tokens; pins are model, effort, adaptive thinking, `max_turns` and `max_budget_usd`; run-to-run agreement measures sampling variance.
- Guidance, Worked Examples, prompts and the Criteria Matrix come from Dev pages only and are frozen and dated before any Evaluation Run.
- Scoring reads only stored files and makes no API calls; Runs are never rewritten.
- Only synthetic Seeded Page content and prompts leave the machine; provider data-retention and training terms are read and dated before the first LLM Run.
- Cost Cap is enforced in code; a Run stopped at the cap never resumes silently.
- Output is guidance, never a compliance claim; pages are English, left-to-right.
- The architecture spine's AD-1 to AD-16 bind all builds (adopted companion).

## Non-goals

- System B (single LLM agent), the optional no-tools arm, and any B-vs-C claim in V1.
- Real public pages, W3C Before and After pages, human WCAG-EM labelling, expert audits, Cohen's kappa, usefulness ratings; these form the next-phase baseline set.
- Statistical testing (Wilcoxon, effect sizes, bootstrap intervals) beyond descriptive tables.
- Compliance certification, CI plug-in, hosted service, native mobile apps, time-based media (WCAG 1.2.x), right-to-left scripts, live browsing or real assistive technology, and criterion-split agents.

## Success signal

System A and C each run end to end on every Seeded Page (C three times), the harness produces the A-vs-C metrics table with ranking, coverage and confidence breakdowns from stored files alone, the matching rule passes the T1-T9 fixture, spend stays under the Cost Cap, and a results note reports against H1 including any null result. H1 holding is not required.

## Assumptions

- About 8-10 Seeded Pages; Dev set suggested as the T1-T9 page plus one more.
- Cost Cap about USD 50, unconfirmed; published frontier-model workloads suggest it may be tight.
- Targets: schema-valid at least 95% after retry, grounding at least 90%, one page through C under 5 minutes.
- Seeded pages are LLM-generated, so generator and audit model may share biases; prefer different models.
- Review Screen is FastAPI with Jinja (user said "Streamlit or FastAPI").
- V1 numbers are optimistic and indicative only; they show the pipeline works.

## Open Questions

- What is the Cost Cap value after live pricing is checked?
- Which Seeded Pages are Dev versus Test?
- Do hooks fire for in-process SDK MCP tools, and does axe-core 4.14.1 cover the WCAG 2.2 rules used? (AD-5 tests and a capture smoke test must answer.)
- Should the proposal wording on fixed temperature be amended (the SDK cannot set it)?
- Confirm with the supervisor that right-to-left and other scripts stay out of scope.
