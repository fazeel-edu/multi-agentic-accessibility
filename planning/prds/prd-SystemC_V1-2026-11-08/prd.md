---
title: SystemC_V1
status: draft
created: 2026-11-08
updated: 2026-11-21
---

# PRD: SystemC_V1
*Working title — confirm.*

## 0. Document Purpose

This PRD defines SystemC_V1, a one-week Python prototype of the role-based multi-agent accessibility auditor (System C) proposed in the MSc project, plus the evaluation harness that scores it. It is written for Fazeel (builder, researcher and V1 reviewer), the supervisor, and the downstream BMAD workflows (UX, architecture, epics, build). Terms in §3 are used verbatim everywhere. Features in §4 group numbered FRs; assumptions are tagged `[ASSUMPTION]` inline and indexed in §9. It builds on `briefs/brief-SystemC_V1-2026-11-08/brief.md` and `doc/Proposal_V1.1.pdf` (latest; supersedes Proposal v2 and the Roadmap, which are not in the repo). Implementation choices (stack, repo layout, schemas, role spec example) live in `addendum.md`.

**Revision 2026-11-21.** Scope is System C plus the System A (axe-core) baseline. System B (single LLM agent) is deferred to a later arm (§6.3). FRs were renumbered; System A is FR-37 and FR-38 (§4.8); the old B runner and parity FRs are deferred, not deleted. **The V1 Page Set is synthetic (Seeded Pages) only.** Real public Pages, W3C BAD Pages and human-evaluated Pages come in a later phase as the baseline set (§6.3). Build order: System C template first (Orchestrator, Role Specs, schema, hooks, post-processing), then System A, Seeded Pages with Ground Truth, harness, Review Screen.

## 1. Vision

Rule engines such as axe-core find accessibility problems quickly but cover only part of WCAG 2.2. Many barriers need judgement. A language-model auditor can judge them, but without discipline it floods reviewers with false alarms.

SystemC_V1 proves, end to end and in one week, that an audit split **by user role** (screen reader, keyboard, colour and visual, cognitive, plain language, WCAG structure, plus a synthesis agent) can run reproducibly, and produces the first honest numbers on what it finds and what it costs in false positives, tokens and money. V1 runs System C beside the axe-core baseline (System A) on the same Pages, so the comparison with a rule engine is measured. Whether C also beats a single LLM agent (System B) is left to the full dissertation evaluation; V1 reports against H1 (§7) accordingly.

V1 is also dissertation evidence: a de-risked build and a reusable harness, ahead of the formal 25-30 page, expert-checked evaluation. A null or negative result is a valid, reportable outcome. The tool gives guidance; it never certifies compliance.

## 2. Target User

### 2.1 Jobs To Be Done
- **Builder-researcher (Fazeel):** run System C on the Page Set with one command per stage, and get a trustworthy metrics table, so weeks 3-10 of the dissertation can be steered by evidence.
- **Builder-researcher:** discover early where agent design, cost, run-to-run variance and ground-truth labelling break, before the schedule depends on them.
- **Reviewer (Fazeel in V1):** read one ranked, evidence-backed report per page and decide which issues are real, without re-auditing the whole page.

### 2.2 Non-Users (v1)
- Developers expecting CI integration, or site owners expecting a compliance certificate.
- Participants with disabilities and external experts: V1 involves no human participants. Expert audits, consent and Cohen's kappa wait for ethics approval (dissertation roadmap).

### 2.3 Key User Journeys

- **UJ-1. Fazeel runs System C and reads the numbers.**
  - **Persona + context:** Fazeel, MSc student, one week to a working harness, API budget capped.
  - **Entry state:** Seeded Pages built, captured and cached; Ground Truth written with each Seeded Page before any system output exists; provider terms checked and dated; Config pins model, effort, loop cap and per-session budget.
  - **Path:** runs System A on all Pages; runs System C three times on the Dev Set while tuning prompts; reads the cost estimate; freezes prompts; runs the final Evaluation Run (System A once, System C 3 Runs per Page); opens the metrics table.
  - **Climax:** one table shows precision, recall and F1 for A and C overall and by issue type and page type, plus ranking quality, WCAG coverage, confidence vs precision, per-Role contribution, tokens, cost and seconds per Page, and cost per true positive.
  - **Resolution:** results are stored as JSONL per Run and Page; a short results note records the outcome against H1, including any null result.
  - **Edge case:** the Cost Cap is reached mid-run; the run stops cleanly, reports what completed, and does not resume silently.

- **UJ-2. Fazeel reviews a page report and signs off.**
  - **Persona + context:** Fazeel as Reviewer, checking System C output on one Page.
  - **Entry state:** a Report for the Page exists; the Ground Truth was committed before the Report existed.
  - **Path:** opens the Review Screen; reads the ranked Issues with element, Criterion, Roles, evidence, suggested fix and Confidence; marks each Issue accepted, rejected, or unsure.
  - **Climax:** sees at a glance which Issues cite evidence that exists in the Capture and which do not.
  - **Resolution:** decisions are saved beside the Report; the Report states what the system cannot test.
  - **Edge case:** an Issue cites an element not in the Capture; it is flagged ungrounded and cannot be accepted without an override note.

## 3. Glossary

- **Page** — a single web page evaluated by the system, identified by a stable `page_id`.
- **Page Set** — all Pages in V1: Seeded Pages only (W3C BAD Pages and Real Pages are a later phase). Split into a **Dev Set** (used to build and tune prompts, guidance and examples) and a **Test Set** (never used for tuning).
- **Page Type** — one of e-commerce, government and public service, forms, content and news, or mobile-sized screenshot.
- **Site Code** — an anonymous label (Site A to Site N) used for a Page in any write-up.
- **Seeded Page** — a synthetic local HTML Page generated by an LLM and reviewed by hand by Fazeel for one Page Type, with planted defects, clean controls and decoys; Ground Truth is known by construction.
- **Decoy** — an element that looks like a defect but is correct (for example a decorative icon hidden from assistive technology), planted so false positives are measurable.
- **W3C BAD Page** (later phase) — a page from the W3C Before and After Demonstration, "before" (defect-heavy) or "after" (clean).
- **Real Page** (later phase) — a public Page saved as a local snapshot, with its terms of use recorded, labelled by humans.
- **Capture** — the saved artefacts for one Page: HTML, computed styles, accessibility tree, screenshot, keyboard focus trace. Cached locally.
- **Focus Trace** — the keyboard focus sequence recorded during Capture with the same scripted steps for every Page.
- **Criterion** — a WCAG 2.2 Level AA success criterion in scope (about 20, fixed in the Criteria Matrix).
- **Criteria Matrix** — the dated mapping of Criteria to issue type (R rule-checkable, J judgement-based, M mixed) and to primary Roles; some Criteria sit under two Roles on purpose. Frozen before any Evaluation Run.
- **Role** — a user-facing perspective: screen reader, keyboard, colour and visual, cognitive, plain language, WCAG structure. Roles are needs or interaction perspectives, not medical labels.
- **Role Spec** — one versioned file per Role with six parts: role prompt, Criteria subset, input artefacts, tool allowlist, output schema, worked examples.
- **Guidance** — a short section in each Role prompt: what to inspect, exceptions, how to read tool output.
- **Worked Example** — a short Dev Set case in a Role's examples (3-4 per Role: a clear issue, a clean case with nothing to report, a borderline case).
- **Role Agent** — a subagent that audits one Capture from one Role, using only its Role Spec.
- **Synthesis Agent** — the inclusive-design subagent that runs after the six Role Agents, reads the whole Capture and their combined output, and has no tools.
- **Orchestrator** — ordinary deterministic Python, not an LLM. It owns the workflow: loads the Capture, looks up the fixed Role table, delegates, runs hooks and validation, and runs post-processing. It does not judge accessibility.
- **System A** — axe-core run with WCAG 2.2 AA tags, no LLM; each violation becomes an Issue.
- **System C** — Orchestrator + six Role Agents + Synthesis Agent.
- **Issue** — one reported accessibility problem in the Issue Schema: page, element, criterion, role, evidence, description, suggested fix.
- **Issue Schema** — the single JSON structure agents output (addendum).
- **Confidence** — for a merged Issue, the number of distinct Roles that reported the same element and Criterion (1 to 6), set by code. A signal, not proof.
- **Ground Truth** — the versioned list of true Issues for a Page: one item per affected element, with a list of acceptable Criteria, affected user group, severity and issue type.
- **Acceptable Criteria** — the Criteria any of which counts as correct for a Ground Truth item (for example 2.4.4 and 2.4.6).
- **Match** — a reported Issue matches a Ground Truth item when it names the same element and any acceptable Criterion.
- **TP / FP / FN** — a reported Issue with a Match / without a Match / a Ground Truth item never matched. Each Ground Truth item counts once however many Issues report it. A Role Agent that fails or is dropped leaves its items as FN.
- **Grounded** — an Issue whose cited element exists in the Capture.
- **Run** — one execution of System C on one Page, with stored raw output, tokens, calls, tool-call log and seconds.
- **Evaluation Run** — the final set of Runs after the Prompt Freeze: 3 Runs per Page.
- **Report** — the ranked, de-duplicated, WCAG-mapped output for one Page from one Run.
- **Review Screen** — a minimal local page where the Reviewer reads a Report and marks Issues.
- **Reviewer** — the human who checks a Report; in V1, Fazeel.
- **Config** — version-controlled settings: model ID, effort, loop cap, per-session budget, Criteria Matrix, prompts.
- **Cost Cap** — a hard limit on API spend enforced in code.
- **Prompt Freeze** — a tagged repo state after which no prompt, Guidance, Worked Example, Criteria Matrix or Config change is allowed before the Evaluation Run.

## 4. Features

### 4.1 Page Set and Ground Truth

**Description:** For the V1 run Fazeel builds a synthetic Page Set and its Ground Truth. Seeded Pages give exact Ground Truth by construction, so A and C can be checked quickly. Real Pages and W3C BAD Pages, labelled by humans following WCAG-EM, are a later phase (§6.3). Realizes UJ-1.

#### FR-1: Seeded Pages with planted defects
Fazeel can create Seeded Pages, one or more per Page Type (e-commerce, government and public service, forms, content and news), whose defects cover the in-scope Criteria across R, J and M types.
**Consequences (testable):**
- About 8-10 Seeded Pages exist [ASSUMPTION], covering all four Page Types; together they plant at least one defect per Role.
- One Seeded Page reproduces the T1-T9 example page of Proposal V1.1 §5.6.
- Each Seeded Page also holds clean controls and at least one Decoy, so false positives can occur and be counted.
- Each planted defect appears in the Ground Truth with element, Acceptable Criteria and issue type.
- A mobile-sized variant is optional.
- Seeded Pages are LLM-generated, then reviewed line by line by Fazeel; the manifest records generator model ID, generation date, prompt file and review status per Page. A Page is not usable until reviewed and its Ground Truth matches the reviewed HTML.

#### FR-2: Page Set manifest
The system records every Page in a manifest.
**Consequences (testable):**
- Each Seeded Page has an entry with `page_id`, Page Type, Dev Set or Test Set flag (set before any Evaluation Run), and Site Code.
- Pages are synthetic, public-safe and contain no personal data; no Page requires a login.
- Pages are English, left-to-right only; this limit is stated in the Report and results note.
- (Later phase) Real and W3C BAD Pages add URL, snapshot date, licence or terms note, robots.txt note, and a redaction check before storage or upload.

#### FR-3: Versioned Ground Truth per Page
Ground Truth is stored as versioned files, one per Page, committed with the Page.
**Consequences (testable):**
- Every item has element locator, Acceptable Criteria, affected user group, severity and issue type (R, J or M).
- Repeated problems (five identical "Click here" links) are one item per element.
- Ground Truth is committed before any Run on that Page exists in `results/`.
- Ground Truth also records the Criteria that have no Issue on the Page (needed for WCAG coverage, FR-21).
- (Later phase) Real Page labels follow WCAG-EM and are written before viewing any system output; W3C BAD labels are re-checked against WCAG 2.2.

#### FR-4: Matching rule
The harness applies one written rule: same element and any Acceptable Criterion.
**Consequences (testable):**
- Unit tests cover exact match, acceptable alternative Criterion, wrong Criterion, wrong element, duplicate reports of one item, five repeated items, and element given as CSS selector versus XPath resolving to the same node.
- The T1-T9 fixture yields the expected TP, FP and FN for a hand-built output set.
- Each item is counted once however many Issues report it; the duplicate rate is reported separately.

### 4.2 Capture

**Description:** Playwright loads each Page and saves a Capture. Agents read the saved Capture and call analysis tools on it; no agent drives a live browser. Interaction (the Focus Trace) is recorded during Capture with scripted steps. Captures are cached so repeated Runs never refetch. Realizes UJ-1.

#### FR-5: Capture a Page
The system captures a Page into HTML, computed styles, accessibility tree, screenshot and Focus Trace.
**Consequences (testable):**
- Capture of a Seeded Page produces all five artefacts.
- The Focus Trace uses the same scripted steps for every Page; the script version is recorded.
- A mobile-sized screenshot variant can be requested per Page. [ASSUMPTION: only if time allows; not required for V1 success.]

#### FR-6: Cache and offline replay
**Consequences (testable):**
- A second Run on the same Page makes zero network requests to the Page's origin.
- A Capture records timestamp and tool versions.

#### FR-7: Polite capture
Capture respects robots.txt and applies a low request rate when it fetches any remote Page. Seeded Pages are local files, so this applies in the later phase.
**Consequences (testable):**
- A remote Page disallowed by robots.txt is refused with a logged reason; a Page whose terms forbid automated access is dropped and replaced.

### 4.3 System C: role-based multi-agent

**Description:** The Orchestrator, ordinary code, runs the same decomposition for every Page: Capture, then all six Role Agents in parallel, then the Synthesis Agent, then post-processing. "Choosing the Role" is a lookup in a fixed table, which keeps Runs reproducible and means C's result never depends on routing luck. Each Role Agent starts empty and receives only what its Role Spec names. Role Agents never talk to each other. Realizes UJ-1.

#### FR-8: Orchestrator is deterministic code
**Consequences (testable):**
- The Orchestrator contains no LLM call; it calls each of the six Roles exactly once per Run, in parallel, from a fixed table, then the Synthesis Agent.
- A test fails if a Role is skipped, added or called twice.

#### FR-9: Role Spec per Role
**Consequences (testable):**
- Each Role has one versioned Role Spec file with the six parts (addendum shows an example).
- Each Role Agent's prompt lists only its own Criteria subset from the Criteria Matrix (some Criteria appear under two Roles by design) and its own input artefacts.
- No Role Agent receives another Role Agent's output.

#### FR-10: Guidance and Worked Examples
**Consequences (testable):**
- Each Role has Guidance and 3-4 Worked Examples (clear, clean, borderline) that cover only Criteria in its own subset.
- Examples come from the Dev Set, never from Test Set Pages; Guidance and examples are fixed and dated before any Evaluation Run.
- Example count and prompt size in tokens are reported per Role.

#### FR-11: Least tools, enforced
**Consequences (testable):**
- Each Role Agent's tool list matches the Config (axe-core, contrast calculator, readability scorer, focus-trace reader as assigned in the addendum).
- A pre-tool hook logs every tool call (tool, arguments, Role, time) and blocks any tool not on the Role's allowlist; a test fails if an unassigned tool call goes through.
- Role Agents are read-only: no file writes, shell, network or browser control.
- A loop-iteration cap per Role Agent is set in Config.

#### FR-12: Parallel Role Agents with explicit context
**Consequences (testable):**
- Six Role Agents run in parallel on one Page; each prompt contains its Capture slice, Criteria subset, Guidance, Worked Examples, tool list and Issue Schema.
- Seconds per Page are recorded for the parallel stage and the whole Run.

#### FR-13: Schema validation and one retry
**Consequences (testable):**
- A post-run hook rejects output that fails the Issue Schema or lacks evidence and retries once; a second failure is logged and the Role Agent's Issues are dropped for that Page.
- Schema-valid rate, evidence-present rate and retry rate are recorded per Role Agent.

#### FR-14: Synthesis Agent after the six
**Consequences (testable):**
- The Synthesis Agent starts only after all Role Agents finish (or fail), reads the whole Capture and the six outputs, and has no tools.
- Its Issues are tagged with role `inclusive_design`; pattern-level notes (for example "this form is hard to finish for a low-vision user") are priority statements, not new Issues, unless they name an element and Criterion.

#### FR-15: Failure isolation
**Consequences (testable):**
- If one Role Agent errors, the other Role Agents' Issues are still reported and the failure is recorded in the Run.
- A failed or dropped Role Agent's Ground Truth items count as FN in recall (never excluded); failures are also reported separately.

### 4.4 Post-processing and Report

**Description:** Deterministic Python, not an LLM, turns raw Issues into a Report. Realizes UJ-1, UJ-2.

#### FR-16: De-duplicate and set Confidence
**Consequences (testable):**
- Issues with the same element and Criterion merge into one Issue listing every reporting Role.
- Confidence equals the number of distinct Roles on the merged Issue (1-6); agents do not set it.

#### FR-17: Map, score, rank
**Consequences (testable):**
- Every Issue carries a WCAG 2.2 Criterion, a severity score and a rank; the ranking rule is documented and unit-tested.

#### FR-18: Report output
**Consequences (testable):**
- A Report is written as JSON per Run and Page, including a "what the system cannot test" statement: no real assistive technology, no live browsing, no users with disabilities, no multi-page journeys; not a compliance certificate.

### 4.5 Evaluation harness

**Description:** Computes the metrics that describe System C. Written and dry-run before the Evaluation Run. Realizes UJ-1.

#### FR-19: Precision, recall and F1
**Consequences (testable):**
- Computed per system (A and C) overall, per issue type (R/J/M) and per Page Type, and for C per Role, from TP, FP and FN under FR-4; results are broken down so gaps by Role, issue type and Page Type are visible, not averaged away.

#### FR-20: Ranking quality
**Consequences (testable):**
- Precision at top 10 and Spearman rank correlation between each system's rank (A and C) and Fazeel's Ground Truth severity are reported.

#### FR-21: WCAG coverage
**Consequences (testable):**
- Coverage, for A and C, is the share of in-scope criterion-Page pairs where the system either flags a valid Issue or correctly reports none where the Page has no Issue. Requires Ground Truth to state which Criteria have no Issue on each Page.

#### FR-22: Confidence vs precision
**Consequences (testable):**
- Precision of Issues reported by 1, 2 and 3 or more Roles is reported, so the Confidence flag can be judged.

#### FR-23: Cost and time
**Consequences (testable):**
- Calls, input and output tokens, seconds and estimated USD per Run; cost per true positive. System A reports seconds and zero API cost.

#### FR-24: Agent behaviour metrics
**Consequences (testable):**
- Schema-valid rate, evidence-present rate, grounding rate, retry rate per Role, tool-call counts from the hook log, and run-to-run agreement over 3 Runs are reported.

#### FR-25: Per-Role contribution and ablation
**Consequences (testable):**
- Role-scoped recall on items tagged with that Role's user group, unique contribution per Role, and Issues found only by the Synthesis Agent are reported.
- A role-removal ablation re-runs System C with one Role removed, and with the Synthesis Agent removed. [ASSUMPTION: runs only if time allows; cut to 2-3 variants before cutting repeats.]

#### FR-26: Results table and results note
**Consequences (testable):**
- One command produces the A vs C metrics table as Markdown and CSV from stored JSONL.
- A results note reports A and C against H1 descriptively, lists findings including null or negative outcomes, and states the real-Page labelling limit and that no single-agent baseline (System B) was run.

#### FR-27: Storage
**Consequences (testable):**
- Raw output is stored as JSONL per Run and Page; metrics can be recomputed from storage without calling any API.

### 4.6 Review Screen

**Description:** A minimal local screen where the Reviewer reads a Report and marks Issues. It exists to prove the human-in-the-loop step, not to be polished. Realizes UJ-2.

#### FR-28: Show a Report
**Consequences (testable):**
- Lists Issues ranked, with element, Criterion, Roles, evidence, description, suggested fix, Confidence and a Grounded flag.

#### FR-29: Record decisions
**Consequences (testable):**
- The Reviewer can mark each Issue accepted, rejected or unsure and save; decisions are stored beside the Report.
- An ungrounded Issue cannot be accepted without an override note.

#### FR-30: Guidance statement
**Consequences (testable):**
- Every screen states that the output is guidance, not a compliance certificate.

### 4.7 Run control, cost and reproducibility

#### FR-31: Pinned Config
**Consequences (testable):**
- Model ID, effort, adaptive thinking, loop cap (`max_turns`), per-session budget (`max_budget_usd`), prompts and Criteria Matrix live in version-controlled Config; every Run records the Config hash and SDK, CLI and tool versions.
- Temperature, top_p and a token cap are not pinned: the Claude Agent SDK does not expose them (checked against current docs 2026-11-21). SDK sampling defaults are a stated limit; run-to-run agreement over 3 Runs measures their effect.

#### FR-32: Cost Cap
**Consequences (testable):**
- Before any LLM Run, the system prints an estimated cost; spend is tracked in code and the Run stops cleanly when the Cost Cap is reached. [ASSUMPTION: Cost Cap about USD 50 for the week; may be tight against published frontier-model workloads, so check live pricing.]

#### FR-33: Dev versus final model
**Consequences (testable):**
- Dev iteration uses the dev model on Dev Set Pages only; the Evaluation Run refuses to start unless every Role Agent and the Synthesis Agent use the same final model ID.

#### FR-34: Prompt Freeze
**Consequences (testable):**
- The repo is tagged at Prompt Freeze; the Evaluation Run refuses to start if prompts, Guidance, Worked Examples, Criteria Matrix or Config differ from the tag. This is a prototype freeze; the dissertation system is frozen at the end of week 9.

#### FR-35: Provider terms gate
**Consequences (testable):**
- Before the first LLM Run, the provider's terms on data retention, training use and zero-retention are read and the date is recorded in the repo; the first LLM Run refuses to start without that record. Only public Page content is sent.

#### FR-36: One command per stage
**Consequences (testable):**
- Capture, each system, evaluation and the Review Screen each start from one documented command.

### 4.8 System A: axe-core baseline

**Description:** Rule-engine baseline on the same Capture as System C. No LLM, so it is cheap and repeatable. Realizes UJ-1.

#### FR-37: Run axe-core with WCAG 2.2 AA tags
**Consequences (testable):**
- Each violation becomes an Issue in the Issue Schema, mapped to its Criterion; role is `axe_core`.
- "Needs review" results are stored separately and excluded from precision and recall.
- System A reads the same Capture as System C and sends nothing to a model.

#### FR-38: System A is deterministic
**Consequences (testable):**
- Two Runs of System A on one Capture produce identical Issues.
- System A Issues go through the same de-duplication, mapping and ranking as System C (FR-16, FR-17) so the metrics table is like for like. Confidence is 1 for every System A Issue.

**Cross-cutting NFRs:** see §5.

## 5. Cross-Cutting NFRs, Constraints and Guardrails

- **Reproducibility:** pinned model ID and settings, cached Captures, versioned Role Specs; any Run can be repeated from stored Config and Capture.
- **Cost:** loop and per-session budget caps; prompt caching used where the Capture prefix is shared; Cost Cap enforced in code (FR-32).
- **Quality targets (V1, indicative):** schema-valid rate at least 95% after retry; grounding rate at least 90%. [ASSUMPTION: starting targets; V1 reports them either way.]
- **Performance:** one Page through System C completes in under 5 minutes on a developer laptop. [ASSUMPTION]
- **Data and legal:** V1 Pages are synthetic, so no third-party content or personal data is captured or sent to the model API. In the later phase: public content only, no login-gated Pages, robots.txt and terms recorded, snapshots kept private, findings naming an organisation's failures not published without permission, Site Codes in write-ups.
- **Guidance, not certification:** no output may claim a Page is compliant or accessible; a clean Report is not proof of accessibility. No claim of compliance with the Equality Act, ADA, EN 301 549 or UAE law.
- **Label leakage:** Ground Truth is written before any system output exists; Guidance, Worked Examples and prompts are tuned only on Dev Set Pages and never copy defects from Test Set Pages.
- **Single input:** System A and System C read the same cached Capture.
- **Limits stated:** Role Agents simulate screen-reader and keyboard use via the accessibility tree and a scripted Focus Trace; they are not real assistive technology. Seeded Pages and their Ground Truth come from the same person who writes the prompts, and synthetic defects are usually cleaner and easier than real-world ones, so V1 numbers are optimistic and indicative only; they say the pipeline works, not how C performs on real sites. English, left-to-right Pages only.
- **Bias visibility:** results are broken down by Role, issue type and Page Type. The cognitive and plain-language Roles rest on judgement, where model bias is most likely; the error analysis looks for systematic misses there.
- **Form factor:** Python command-line pipeline plus a local Review Screen; no hosted service.

## 6. Non-Goals and MVP Scope

### 6.1 Non-Goals
- Not a compliance or certification tool; not a CI plug-in; not a SaaS.
- Not a re-implementation of the criterion-split system (Mishra et al., 2026); no head-to-head claim.
- Not a user-research platform; no participants.

### 6.2 In Scope for V1 (7 days)
Capture and cache; System A (axe-core baseline); Orchestrator, six Role Agents and Synthesis Agent (System C); Role Specs, Guidance and Worked Examples; hooks; deterministic post-processing; Report JSON; Review Screen; evaluation harness with the metrics in §4.5; Cost Cap, provider-terms gate and Prompt Freeze; about 8-10 Seeded Pages across all Page Types. Build order: System C template first, then System A, Seeded Pages and Ground Truth, harness, Review Screen.

### 6.3 Out of Scope for V1
- **Deferred to a later arm (dissertation roadmap; schema and harness stay compatible):** System B (single LLM agent given the same Capture, tools, criteria, Guidance, Worked Examples, model, settings and post-processing as C, so that the split is the only difference); the parity check between B and C; optional B0 (single agent, no tools, no Guidance); B-vs-C comparisons. Until B exists, the part of H1 that compares C with a single agent cannot be answered.
- **Deferred to the next phase (human-evaluated baseline set):** Real public Pages (GOV.UK guidance, Wikipedia, a testing-friendly shop, optional UAE portal) and W3C Before and After Pages, with page-terms table, robots.txt checks, redaction checks, WCAG-EM manual labelling, and the 25-30 Page evaluation. They plug into the same harness without changes.
- Literature review, ethics application, expert recruitment, Cohen's kappa and expert usefulness ratings; the full 25-30 Page set and licence table; optional Mishra external check; native mobile apps; time-based media (WCAG 1.2.x); right-to-left and other scripts; compliance certification.
- Statistical testing (Wilcoxon, effect sizes, bootstrap intervals) beyond descriptive tables. [NOTE FOR PM: revisit if time remains on day 7.]

## 7. Success Metrics

**Hypothesis H1 (Proposal V1.1 §6.6), reported not gated.** On the same Pages and Ground Truth, C has higher recall than axe-core and than a single agent, with precision no more than 10 percentage points below the single agent, and the gain is largest on judgement-based Criteria. V1 measures the axe-core half directly (A vs C on the same Pages and Ground Truth) but has no System B, so the results note reports the single-agent half (recall above B, precision within 10 points of B) as not yet tested. It also lists C's recall and precision next to Mishra et al.'s published figures (axe-core 36% / 90%; uncued vision-language model 67% / 61%; their workers 86% / 56%; different pages and Ground Truth, so context only).

**Primary**
- **SM-1:** Pipeline completeness — System A produces a valid stored Run and System C 3 valid stored Runs for 100% of Pages. Validates FR-5, FR-8, FR-12, FR-27, FR-37.
- **SM-2:** Metrics table produced — precision, recall, F1 for A and C overall and by issue type and Page Type, and for C by Role; ranking quality, WCAG coverage, Confidence vs precision; cost per Page and per true positive. Validates FR-19 to FR-23, FR-26.
- **SM-3:** Harness sanity — System A recovers at least 90% of the planted R-type defects on Seeded Pages; on the T1-T9 Seeded Page a hand-built "perfect" output scores precision and recall 1.0 and a hand-built partial output scores the expected TP, FP and FN. A lower value means Ground Truth or the matching rule is wrong. Validates FR-1, FR-3, FR-4, FR-37.

**Secondary**
- **SM-4:** Schema-valid rate at least 95% and grounding rate at least 90%. Validates FR-13, FR-24.
- **SM-5:** Guardrails verified — no off-allowlist tool call succeeds in the hook log; Evaluation Run refused when frozen state differs. Validates FR-11, FR-33, FR-34, FR-35.
- **SM-6:** Total spend at or under the Cost Cap. Validates FR-32.
- **SM-7:** Results note names at least three concrete lessons for dissertation weeks 3-10, including any null result. Validates FR-26.

**Counter-metrics (do not optimise)**
- **SM-C1:** Recall alone — do not chase recall at the expense of precision; report both. Counterbalances SM-2.
- **SM-C2:** Dev-set score — do not tune prompts, Guidance or Worked Examples on Test Set or Real Pages; a high Dev Set score is not a result. Counterbalances SM-2, SM-3.
- **SM-C3:** Cost minimisation — do not cut Runs or repeats until variance can no longer be measured. Counterbalances SM-6.

H1 holding is explicitly not a success criterion.

## 8. Open Questions
1. Confirm the Cost Cap (about USD 50) once live pricing is checked in the architecture step; compare with Mishra et al.'s USD 37-65 worker workloads.
2. Confirm the Seeded Page list (one or two per Page Type) and the Dev Set versus Test Set split (suggested: the T1-T9 page plus one more as Dev Set, the rest Test Set).
3. Resolved 2026-11-21: Seeded Pages are LLM-generated, then reviewed by hand by Fazeel, with the generator model recorded per Page.
4. Review Screen form: static HTML plus a small local server, or a lightweight Python UI? (Decided in architecture/UX.)
5. Right-to-left and other scripts are out of scope; confirm with the supervisor (V1.1 §10.2(d)).
6. Resolved 2026-11-21: System B deferred, System A kept in V1.

## 9. Assumptions Index
- FR-1 — about 8-10 Seeded Pages; V1 Page Set is synthetic only (user decision 2026-11-21).
- FR-5 — mobile screenshot variant is optional.
- FR-1 — generator model may share biases with the audit model (self-agreement risk); recorded, not eliminated. Prefer a generator different from the audit model.
- FR-25 — ablation only if time allows.
- FR-32 and §5 — Cost Cap about USD 50.
- §5 — schema-valid at least 95%, grounding at least 90%, one Page under 5 minutes.
- §7 — H1 is reported, not required (from the brief).
- §0, §6.3 — System B deferred, System A kept in V1 (user decision 2026-11-21).
