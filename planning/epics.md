---
status: final
stepsCompleted: [1, 2, 3, 4]
inputDocuments:
  - specs/spec-systemc-v1/SPEC.md
  - specs/spec-systemc-v1/glossary.md
  - specs/spec-systemc-v1/criteria-matrix.md
  - prds/prd-SystemC_V1-2026-11-08/prd.md
  - prds/prd-SystemC_V1-2026-11-08/addendum.md
  - architecture/architecture-SystemC_V1-2026-11-21/ARCHITECTURE-SPINE.md
---

# SystemC_V1 - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for SystemC_V1, decomposing the requirements from the spec, PRD and architecture spine (AD-1 to AD-16) into implementable stories. No UX design document exists; the Review Screen's accessibility rules come from AD-13. Build order: System C template first, then System A, seeded pages and ground truth, harness, review screen.

## Requirements Inventory

### Functional Requirements

FR numbers match the PRD (FR-n here is FRn).

FR1: Seeded Pages across the four Page Types with planted defects (at least one per Role), clean controls and Decoys; one reproduces T1-T9; LLM-generated then hand-reviewed with generator model recorded.
FR2: Page Set manifest: page_id, Page Type, Dev/Test flag, Site Code, generator model, review status, HTML hash, pinned capture_hash; English LTR; no personal data.
FR3: Versioned ground truth per page: element, acceptable criteria, user group, severity, R/J/M type, per-page no-issue criteria; committed before any Run.
FR4: Matching rule: same element and any acceptable criterion; each item counted once; repeated problems one item per element; duplicate rate reported; unit tests listed in PRD.
FR5: Capture HTML, computed styles, accessibility tree, screenshot, scripted focus trace (plus axe results and contrast, per AD-3); optional mobile variant.
FR6: Cache and offline replay; zero requests to origin on second Run; record timestamp and tool versions.
FR7: Polite capture respecting robots.txt (deferred to the real-page phase; Seeded Pages are local files).
FR8: Orchestrator is deterministic code; each of six Roles called exactly once, in parallel, from a fixed table; test fails if skipped, added or repeated.
FR9: One versioned Role Spec per Role with six parts; each Role sees only its criteria subset and inputs; no cross-role output.
FR10: Guidance and 3-4 Worked Examples per Role from Dev pages only, fixed and dated; example count and prompt tokens reported.
FR11: Least tools per Role, enforced by a hook that logs and blocks off-allowlist calls; read-only; loop cap in Config.
FR12: Six Role Agents run in parallel with explicit context; seconds per page recorded.
FR13: Schema validation, evidence required, one retry, then role failed; per-Role valid/evidence/retry rates.
FR14: Synthesis Agent after the six, no tools, role `inclusive_design`; priority statements are not Issues.
FR15: Failure isolation; failed Role's issues dropped and reported separately.
FR16: De-duplicate on element and criterion; Confidence = distinct Roles (1-6) set by code.
FR17: Map to WCAG 2.2 criterion, severity, rank; ranking rule documented and unit-tested.
FR18: Report JSON per Run and page with "what the system cannot test" statement.
FR19: Precision, recall, F1 per system, issue type, Page Type and (C) per Role.
FR20: Ranking quality: precision at top 10 and Spearman vs ground-truth severity.
FR21: WCAG coverage of criterion-page pairs including correct "none".
FR22: Confidence vs precision for 1, 2, 3+ Roles.
FR23: Calls, tokens, seconds, estimated USD per Run; cost per true positive; A reports seconds only.
FR24: Agent behaviour: schema-valid, evidence-present, grounding, retry rates, tool-call counts, run-to-run agreement over 3 Runs.
FR25: Per-Role recall, unique contribution, Synthesis-only issues; role-removal ablation including removing synthesis (if time).
FR26: One command writes the A-vs-C table as Markdown and CSV; results note against H1 incl. null results and limits.
FR27: Raw output stored as JSONL per Run and page; metrics recomputable with no API call.
FR28: Review Screen lists ranked Issues with element, criterion, Roles, evidence, description, fix, Confidence, grounded flag.
FR29: Reviewer marks accepted/rejected/unsure; decisions stored beside Report; ungrounded needs override note.
FR30: Every screen states guidance, not a compliance certificate.
FR31: Pinned Config (model, effort, thinking, max_turns, max_budget_usd, prompts, matrix); Config hash and SDK/CLI/tool versions per Run; temperature, top_p, max_tokens not pinned (SDK cannot).
FR32: Cost estimate before LLM Runs; Cost Cap hard stop; no silent resume.
FR33: Dev model on Dev pages only; Evaluation Run requires one final model ID.
FR34: Prompt Freeze git tag; Evaluation Run refuses on any drift.
FR35: Provider-terms gate: dated record before first LLM Run.
FR36: One documented command per stage.
FR37: System A runs axe-core with WCAG 2.2 AA tags; violations become Issues; needs-review stored apart.
FR38: System A deterministic; passes through the same post-processing; Confidence 1.

### NonFunctional Requirements

NFR1: Reproducibility: pinned model ID and settings, cached Captures, versioned Role Specs, Config hash per Run.
NFR2: Cost control: loop and per-session budget caps; prompt caching for shared Capture prefix; Cost Cap enforced in code.
NFR3: Quality targets (indicative): schema-valid at least 95% after retry; grounding at least 90%.
NFR4: Performance: one page through System C under 5 minutes on a laptop.
NFR5: Data/legal: synthetic content only in V1; provider terms read and dated; API key from environment only, never logged.
NFR6: Guidance not certification: no output claims a page is compliant.
NFR7: Label leakage control: ground truth before any output; prompts tuned on Dev pages only.
NFR8: Limits stated: simulated assistive technology; builder-written synthetic pages; English LTR.
NFR9: Form factor: Python CLI plus local Review Screen; no hosted service.
NFR10: Bias visibility: results broken down by Role, issue type, Page Type.

### Additional Requirements

- Greenfield Python project (no starter template named): uv-managed Python 3.12 package with the layout in the spine (config, contract, capture, tools, auditors, postprocess, eval, store, review, cli, tools_dev, data, results, tests). First story.
- Stack pins verified 2026-11-21: claude-agent-sdk 0.2.187 (>=0.2.177), Playwright 1.65.2, axe-core 4.14.1 (vendored), pydantic 2.14.4, FastAPI 0.165.0; re-verify at pin time.
- AD-1 Auditor port; AD-2 one contract with closed enums and code-set fields; AD-3 immutable complete captures with one pinned capture_hash per page; AD-4 isolated SDK sessions via asyncio; AD-5 fail-closed hook, `tools=[]`, per-role MCP server, `allowed_tools`; AD-6 output gate; AD-7 hashed Config, adaptive thinking, explicit effort; AD-8 reserve/settle ledger; AD-9 named immutable files; AD-10 only postprocess maps criteria; AD-11 one matching module; AD-12 Dev/Test checks; AD-13 review as file client; AD-14 offline page generation; AD-15 single element_key; AD-16 failure, provider and ops envelope (secrets, .gitignore, backup, batch runner).
- Required smoke tests before relying on SDK behaviour: hooks fire for in-process MCP tools; raising hook blocks; axe-core 4.14.1 WCAG 2.2 rule coverage; `task_budget` effect (advisory).
- Package dependency rules enforced by an import-linter style test (spine dependency graph).
- Environments: local only; dev (Haiku, Dev pages) and eval (Sonnet, frozen config, Test pages).

### UX Design Requirements

No UX design document exists. Review Screen constraints come from AD-13: server-rendered semantic HTML, accessible by construction, guidance statement on every screen.

### FR Coverage Map

FR1: Epic 4 - Seeded Pages with defects, controls, decoys (T1-T9 fixture first in Epic 1)
FR2: Epic 4 - Page Set manifest, Dev/Test flags, pinned capture_hash
FR3: Epic 4 - Versioned ground truth bound to the pinned Capture
FR4: Epic 5 - Matching rule and tests
FR5: Epic 1 - Capture artifacts
FR6: Epic 1 - Cache and offline replay
FR7: Deferred - robots.txt, real-page phase
FR8: Epic 2 - Deterministic orchestrator, fixed role table
FR9: Epic 2 - Role Specs, criteria subsets, no cross-role output
FR10: Epic 2 - Guidance and Worked Examples (frozen in Epic 6)
FR11: Epic 2 - Least tools enforced by hook
FR12: Epic 2 - Parallel roles, seconds per page
FR13: Epic 2 - Schema validation and one retry
FR14: Epic 2 - Synthesis Agent
FR15: Epic 2 - Failure isolation
FR16: Epic 2 - Dedupe and Confidence
FR17: Epic 2 - Map, score, rank
FR18: Epic 2 - Report with cannot-test statement
FR19: Epic 5 - P/R/F1 breakdowns
FR20: Epic 5 - Ranking quality
FR21: Epic 5 - WCAG coverage
FR22: Epic 5 - Confidence vs precision
FR23: Epic 5 - Cost and time metrics
FR24: Epic 5 - Agent behaviour metrics
FR25: Epic 5 - Per-Role contribution and ablation
FR26: Epic 6 - Results table and note
FR27: Epic 2 (Run storage) and Epic 5 (offline recompute)
FR28: Epic 7 - Show a Report
FR29: Epic 7 - Record decisions
FR30: Epic 7 - Guidance statement
FR31: Epic 1 - Config hash and versions
FR32: Epic 2 - Cost estimate and Cost Cap
FR33: Epic 6 - Dev vs final model
FR34: Epic 6 - Prompt Freeze
FR35: Epic 2 - Provider terms gate
FR36: Epics 1, 2, 3, 5, 6, 7 - One command per stage, each in the epic that adds the stage
FR37: Epic 3 - System A axe-core runner
FR38: Epic 3 - System A deterministic, shared post-processing

## Epic List

### Epic 1: Capture a page and stand up the project skeleton
Fazeel can set up the repo and capture a page into an immutable, cached Capture that any system can read.
**FRs covered:** FR5, FR6, FR31, FR36 (capture command); partial FR1 (T1-T9 fixture)

### Epic 2: System C audits a page and produces a Report
Fazeel can run six role agents and a synthesis agent on a Capture and get a ranked, evidence-backed Report within budget.
**FRs covered:** FR8-FR18, FR27 (Run storage), FR32, FR35, FR36 (audit command)

### Epic 3: System A baseline
Fazeel can run axe-core on the same Capture and get Issues through the same post-processing. Needs Epic 1 and Story 2.8 (post-processing) only; otherwise parallel to Epic 2.
**FRs covered:** FR36 (axe command), FR37, FR38

### Epic 4: Synthetic page set and ground truth
Fazeel can build about 8-10 reviewed Seeded Pages with decoys and ground truth bound to pinned Captures.
**FRs covered:** FR1, FR2, FR3

### Epic 5: Scoring and metrics
Fazeel can score A and C against ground truth and see detection, ranking, coverage, confidence, cost and behaviour measures.
**FRs covered:** FR4, FR19-FR25, FR27 (offline), FR36 (eval command)

### Epic 6: Freeze, evaluate and report
Fazeel can freeze prompts, run the final Evaluation Run, and produce the A-vs-C table and results note.
**FRs covered:** FR26, FR33, FR34, FR36 (freeze, batch, table commands)

### Epic 7: Review Screen
Fazeel can read a Report and mark each Issue accepted, rejected or unsure.
**FRs covered:** FR28, FR29, FR30, FR36 (review command)

## Epic 1: Capture a page and stand up the project skeleton

Fazeel can set up the repo and capture a page into an immutable, cached Capture that any system can read.

### Story 1.1: Project scaffold and dependency rules

As Fazeel,
I want a uv Python 3.12 project with the spine's package layout and dependency rules,
So that every later story lands in a place that enforces the architecture.

**Acceptance Criteria:**

**Given** a clean checkout
**When** I run the documented setup and `pytest`
**Then** the packages `config, contract, capture, tools, auditors, postprocess, eval, store, review, cli, tools_dev` exist and tests pass
**And** a test fails if a package imports against the spine's dependency graph (for example `eval` importing `auditors`)
**And** `.gitignore` excludes `.env`, `results/` and `data/captures/`, and a pre-commit check blocks key-shaped strings (NFR5, AD-16)
**And** pinned versions for claude-agent-sdk, Playwright, pydantic, FastAPI are re-verified and recorded.

### Story 1.2: Shared contract models and exported schema

As Fazeel,
I want one set of contract models,
So that agents, post-processing, scoring and review share one shape.

**Acceptance Criteria:**

**Given** the contract package
**When** I import `Issue, MergedIssue, GroundTruthItem, Run, Report, Role, Severity, ElementKey`
**Then** `Role` is a closed enum of the eight roles, `Severity` is a closed ordinal enum, and code-set fields are not accepted from agent input (AD-2)
**And** JSON Schema `issue_v1.json` is exported from the models and every model carries `schema_version`
**And** the `Report` model has `cannot_test_statement`, `priority_notes`, `role_status`, `run_id, system, phase, group_id, capture_hash, config_hash, postprocess_version`.

### Story 1.3: Store, Config loader and Config hash

As Fazeel,
I want one module that reads and writes project files and loads a hashed Config,
So that every Run is reproducible.

**Acceptance Criteria:**

**Given** a `config/` folder with model IDs, effort, thinking, `max_turns`, `max_budget_usd` and a Criteria Matrix
**When** `store.config.load()` runs
**Then** it returns a validated Config and a `config_hash` over the whole folder (FR31, AD-7)
**And** changing any file changes the hash
**And** only `store` opens project files; temperature, top_p and max_tokens are absent from Config by design.

### Story 1.4: T1-T9 fixture page

As Fazeel,
I want a hand-built page that reproduces the proposal's T1-T9 defects plus a Decoy,
So that every later story has a known fixture.

**Acceptance Criteria:**

**Given** `data/pages/`
**When** I open the fixture page
**Then** it contains the nine defects of Proposal V1.1 section 5.6 (alt "image123.png", repeated "Click here" links, 2.8:1 contrast, placeholder-only label, red-border-only error, "Invalid" message, modal focus, focus behind sticky header, vague headings)
**And** it contains one clean control and one Decoy (decorative icon correctly hidden)
**And** a draft ground-truth table for it is committed with element selectors, acceptable criteria, type and severity.

### Story 1.5: element_key normaliser

As Fazeel,
I want a single function that turns a selector into a canonical element key,
So that reports and ground truth compare like with like.

**Acceptance Criteria:**

**Given** Capture HTML and a CSS selector or XPath
**When** `tools.element.element_key` runs
**Then** it returns a tagged union `node | nodes | page | unresolved` using one pinned parser (AD-15)
**And** a CSS selector and an XPath resolving to the same node give equal keys
**And** a selector that matches nothing returns `unresolved` and is never treated as grounded.

### Story 1.6: Capture a page

As Fazeel,
I want to capture a page once into an immutable Capture,
So that every system judges identical evidence.

**Acceptance Criteria:**

**Given** a local page path
**When** I run the capture command
**Then** `data/captures/{page_id}/{capture_hash}/` holds HTML, computed styles, accessibility tree, screenshot, scripted focus trace, axe results (including needs-review) and contrast measurements, with `capture.json` listing every artifact and tool and focus-script versions (FR5, AD-3)
**And** `capture_hash` covers only the deterministic list (not screenshot bytes or timestamps) and a re-capture of an unchanged page gives the same hash
**And** a second Run reading the Capture makes zero network requests (FR6).

## Epic 2: System C audits a page and produces a Report

Fazeel can run six role agents and a synthesis agent on a Capture and get a ranked, evidence-backed Report within budget.

### Story 2.1: SDK smoke tests for isolation and the hook

As Fazeel,
I want to prove the Agent SDK behaves as the spine assumes,
So that the tool allowlist is real before roles are built on it.

**Acceptance Criteria:**

**Given** a minimal session with `setting_sources=[]`, `tools=[]`, built-ins in `disallowed_tools` and one in-process MCP tool
**When** the model calls an allowlisted tool and an off-allowlist tool
**Then** the `PreToolUse` hook fires for the MCP call, allows the first and denies the second (AD-5)
**And** a hook that raises blocks the call (`on_failure="block"`, SDK at least 0.2.177)
**And** results record whether `task_budget` changes behaviour and whether `ToolSearch` needs allowlisting; failures are written to the architecture memlog as open questions.

### Story 2.2: Analysis tools over a Capture

As Fazeel,
I want pure analysis tools and their SDK wrappers,
So that role agents can inspect evidence without touching a browser.

**Acceptance Criteria:**

**Given** a loaded Capture
**When** I call the contrast calculator, readability scorer, focus-trace reader or axe-result reader
**Then** each returns deterministic text/JSON from stored artifacts and never launches a browser or the network (AD-3)
**And** each tool has an in-process SDK MCP wrapper registered per role server, with one server entry per role containing only that role's tools
**And** unit tests cover each tool on the T1-T9 fixture (for example 2.8:1 contrast is reported).

### Story 2.3: Cost ledger and Cost Cap

As Fazeel,
I want a single spend ledger with a hard cap,
So that parallel agents cannot overspend.

**Acceptance Criteria:**

**Given** a Cost Cap in Config
**When** sessions reserve and settle spend
**Then** the ledger is append-only JSONL with a file lock, reserve before start and settle from the last `ResultMessage` `total_cost_usd` and `model_usage` without summing cumulative values (AD-8)
**And** when remaining budget cannot cover a reservation no new session starts, in-flight sessions finish, and the Run is marked `stopped_cost_cap` (FR32)
**And** a cost estimate prints before any LLM stage and resume after a stop needs an explicit flag.

### Story 2.4: Provider terms gate

As Fazeel,
I want the first LLM Run blocked until provider terms are read and dated,
So that I meet my ethics commitments.

**Acceptance Criteria:**

**Given** `config/provider_terms.md`
**When** an LLM Run starts without a dated entry covering data retention, training use and zero-retention
**Then** it refuses to start with a clear message (FR35)
**And** with a dated entry it starts and the date is stored in the Run.

### Story 2.5: One role end to end (screen reader)

As Fazeel,
I want the screen-reader role running as an isolated session with its Role Spec,
So that the role template is proven before the others are added.

**Acceptance Criteria:**

**Given** the screen_reader Role Spec (prompt, criteria subset, inputs, tool allowlist, output schema, Guidance, 3-4 Worked Examples)
**When** the role runs on the T1-T9 Capture
**Then** the session uses `setting_sources=[]`, empty temp `cwd`, no skills or agents, receives only its inputs and criteria, and its tool calls are hook-logged (FR9, FR11, AD-4, AD-5)
**And** output is validated against the contract with non-empty `evidence`, retried once on failure, then marked `failed` with `{stage, kind, message, retryable}` (FR13, AD-6)
**And** the Run records prompt size in tokens and example count; examples are drawn from the fixture page as a placeholder source and re-sourced from Dev pages in Story 6.1 (FR10).

### Story 2.6: Orchestrator runs all six roles in parallel

As Fazeel,
I want the fixed role table to run all six roles in parallel,
So that C has no routing variance and one failure cannot sink a Run.

**Acceptance Criteria:**

**Given** the six Role Specs
**When** the orchestrator runs
**Then** it starts exactly one session per role from the fixed table with `asyncio` and records seconds per role and per Run (FR8, FR12)
**And** a test fails if a non-ablation Run skips, adds or repeats a role (AD-4)
**And** a role error or timeout sets that role `failed` while the other roles' issues are still returned, with provider errors retried with bounded backoff (FR15, AD-16)
**And** no role receives another role's output.
**And** the orchestrator accepts an `exclude` set (default empty) recorded on the Run as `variant`, so ablation (Story 5.6) reuses it.

### Story 2.7: Synthesis Agent

As Fazeel,
I want an inclusive-design agent that reads all six outputs,
So that cross-role patterns surface.

**Acceptance Criteria:**

**Given** the six role outputs (some possibly failed)
**When** the Synthesis Agent runs after all six end or fail
**Then** it has no tools and role `inclusive_design`, and its Issues carry `derived_from[]` (FR14, AD-10)
**And** priority statements are stored as `priority_notes`, not Issues
**And** a synthesis failure leaves the six role outputs reported with `synthesis=failed` (AD-16).

### Story 2.8: Post-processing to a Report

As Fazeel,
I want a pure post-processing step,
So that every system produces the same Report shape.

**Acceptance Criteria:**

**Given** an `AuditResult` and the Criteria Matrix
**When** `postprocess.run` executes
**Then** criteria are assigned only here (native `rule_id` expands through the Matrix), duplicates merge on `(element_key, criterion)`, and `confidence` equals the count of distinct reporting roles excluding synthesis echoes (FR16, AD-10)
**And** each Issue has severity, rank and `grounded`; the ranking rule is documented and unit-tested (FR17)
**And** issues with no criterion after mapping go to `Report.unmapped_issues`, kept for review and excluded from matching, ranking and Confidence
**And** the Report includes the "what the system cannot test" statement (FR18).

### Story 2.9: Run storage and the audit command

As Fazeel,
I want one command that audits a page with System C and stores the Run,
So that I can see a first Report and recompute later.

**Acceptance Criteria:**

**Given** a Capture and a valid Config
**When** I run the System C audit command
**Then** `results/role_multi_agent/{page_id}/{run_id}/` holds `run.json, issues.jsonl, tool_calls.jsonl` and a derived `report.{postprocess_version}.json`, never rewritten (FR27, AD-9)
**And** `run.json` records config hash, SDK/CLI/tool versions, phase, model ID, `group_id` and per-role status
**And** the T1-T9 page yields a Report I can read.

## Epic 3: System A baseline

Fazeel can run axe-core on the same Capture and get Issues through the same post-processing.

### Story 3.1: axe auditor behind the Auditor port

As Fazeel,
I want System A as an adapter that reads the Capture's axe results,
So that A and C feed the same harness.

**Acceptance Criteria:**

**Given** a Capture with stored axe results (WCAG 2.2 AA tags)
**When** the axe auditor runs
**Then** it returns an `AuditResult` with each violation as an Issue (role `axe_core`, native `rule_id`, criterion left to post-processing) and sends nothing to a model (FR37, AD-1)
**And** "needs review" results are stored apart and excluded from precision and recall
**And** multi-node violations become `nodes` element keys.

### Story 3.2: System A command, determinism and shared post-processing

As Fazeel,
I want System A to run from one command through the same post-processing,
So that A and C are ranked and merged identically.

**Acceptance Criteria:**

**Given** a Capture
**When** I run the axe command twice
**Then** both Runs produce identical Issues (FR38) and are stored under `results/axe/...` like C Runs
**And** the Report comes from `postprocess.run` with Confidence 1 on every Issue
**And** the Run records seconds and zero API cost.

## Epic 4: Synthetic page set and ground truth

Fazeel can build about 8-10 reviewed Seeded Pages with decoys and ground truth bound to pinned Captures.

### Story 4.1: Page generator and manifest

As Fazeel,
I want an offline generator and a manifest,
So that generated pages are traceable and only reviewed pages enter the set.

**Acceptance Criteria:**

**Given** a page brief (Page Type, planted defects, controls, decoys)
**When** `tools_dev/generate_page.py` runs
**Then** it writes a candidate page and draft ground truth, and records generator model ID, date and prompt file (AD-14)
**And** a page enters `manifest.json` only after Fazeel marks it `reviewed`, with HTML hash stored; changing the HTML resets review status
**And** the manifest holds `page_id, page_type, dev|test, site_code`.

### Story 4.2: Ground-truth files and bind step

As Fazeel,
I want ground truth bound to the pinned Capture,
So that scoring compares element keys, not raw selectors.

**Acceptance Criteria:**

**Given** a ground-truth file with selectors
**When** the `bind-gt` command runs against the pinned Capture
**Then** each item gets an `element_key` via `tools.element` and unresolved selectors fail the command (FR3, AD-15)
**And** each item holds acceptable criteria, user group, expected roles, severity, issue type and scope, and the page records `no_issue_criteria`
**And** the file is versioned in git and committed before any Run for the page exists.

### Story 4.3: E-commerce Seeded Pages

As Fazeel,
I want reviewed e-commerce pages with planted defects, controls and decoys,
So that A and C are tested on shop-style content.

**Acceptance Criteria:**

**Given** the generator and bind step
**When** I produce and review the pages
**Then** one or two pages exist for product, cart or checkout with defects across R, J and M types and at least one Decoy each (FR1)
**And** each is captured, ground truth bound, the `capture_hash` pinned in the manifest and review status `reviewed`.

### Story 4.4: Government and public-service Seeded Pages

As Fazeel,
I want reviewed guidance and application-form pages,
So that A and C are tested on public-service content.

**Acceptance Criteria:**

**Given** the generator and bind step
**When** I produce and review the pages
**Then** one or two pages exist with planted headings, link-purpose, language and form defects plus controls and decoys
**And** each is captured, bound and pinned as in Story 4.3.

### Story 4.5: Forms Seeded Pages

As Fazeel,
I want reviewed forms pages,
So that keyboard, error and labelling defects are covered.

**Acceptance Criteria:**

**Given** the generator and bind step
**When** I produce and review the pages
**Then** one or two pages exist with label, error, focus and modal defects plus controls and decoys
**And** across Stories 4.3-4.6 at least one defect per Role exists (FR1).

### Story 4.6: Content and news Seeded Pages

As Fazeel,
I want reviewed content pages,
So that reading order, headings, contrast and wording are covered.

**Acceptance Criteria:**

**Given** the generator and bind step
**When** I produce and review the pages
**Then** one or two pages exist with reading-order, heading, contrast and plain-language defects plus controls and decoys
**And** each is captured, bound and pinned.

### Story 4.7: Dev/Test split and manifest checks

As Fazeel,
I want the Dev/Test split fixed and checked,
So that prompts never learn from Test pages.

**Acceptance Criteria:**

**Given** the reviewed pages
**When** I run the manifest check
**Then** every page is flagged `dev` or `test`, the T1-T9 page and one more are `dev`, the rest `test`, and every page has a pinned `capture_hash` (FR2, AD-12)
**And** the hand-built T1-T9 fixture page is registered in the manifest after review
**And** the check fails if any page is unreviewed, any ground truth is missing, or ground truth was committed after the first Run for that page.

## Epic 5: Scoring and metrics

Fazeel can score A and C against ground truth and see detection, ranking, coverage, confidence, cost and behaviour measures.

### Story 5.1: Matching rule

As Fazeel,
I want one tested matching rule,
So that A and C are scored identically.

**Acceptance Criteria:**

**Given** a Report and ground truth
**When** `eval.match` runs
**Then** an Issue matches when `element_key` is equal and its criterion is in `acceptable_criteria`; each item counts once; surplus matches are duplicates, not TP; repeated problems count per element (FR4, AD-11)
**And** unit tests cover exact, acceptable alternative, wrong criterion, wrong element, duplicates, five repeated items, and selector versus XPath
**And** the T1-T9 fixture with a hand-built output gives the expected TP/FP/FN.

### Story 5.2: Precision, recall and F1 breakdowns

As Fazeel,
I want P/R/F1 by system, issue type, Page Type and Role,
So that gaps are visible, not averaged away.

**Acceptance Criteria:**

**Given** stored Reports for A and C
**When** I run the eval command
**Then** precision, recall and F1 are reported overall and per R/J/M type and Page Type, and for C per Role (FR19)
**And** a failed role lowers recall only through its missing issues and appears in role-scoped metrics
**And** the duplicate rate is reported separately.

### Story 5.3: Ranking quality and WCAG coverage

As Fazeel,
I want ranking and coverage measures,
So that I can judge usefulness beyond detection.

**Acceptance Criteria:**

**Given** Reports and ground truth with severities and `no_issue_criteria`
**When** metrics run
**Then** precision at top 10 and Spearman rank correlation against ground-truth severity are reported per system (FR20)
**And** WCAG coverage counts criterion-page pairs where the system flags a valid issue or correctly reports none (FR21).

### Story 5.4: Confidence, per-Role contribution and synthesis-only issues

As Fazeel,
I want to see whether Confidence and each Role add value,
So that the role split can be judged.

**Acceptance Criteria:**

**Given** C Reports
**When** metrics run
**Then** precision is reported for issues with Confidence 1, 2 and 3 or more (FR22)
**And** role-scoped recall on items tagged with each role's user group, each role's unique contribution, and issues found only by the Synthesis Agent are reported (FR25).

### Story 5.5: Cost, time and behaviour metrics

As Fazeel,
I want cost, time and agent-behaviour numbers,
So that I understand what C costs and how reliable it is.

**Acceptance Criteria:**

**Given** stored Runs
**When** metrics run
**Then** calls, tokens, seconds and estimated USD per Run and cost per true positive are reported, with A at zero API cost (FR23)
**And** schema-valid, evidence-present, grounding and retry rates per role, tool-call counts from the hook log, prompt size and example count, and run-to-run agreement over the 3 Runs per `group_id` are reported (FR24, FR10)
**And** costs are labelled SDK estimates.

### Story 5.6: Role-removal ablation

As Fazeel,
I want to re-run C with one role (or the synthesis agent) removed,
So that I see which parts add value.

**Acceptance Criteria:**

**Given** the orchestrator and Config
**When** I run the ablation command with an exclude set
**Then** the same orchestrator runs without those roles and the Run records `variant` (FR25, AD-4)
**And** ablation Runs are scored by the same eval and shown beside the full C results
**And** if time is short, the ablation is cut to 2-3 variants before repeats are cut.

### Story 5.7: Offline recompute and integrity checks

As Fazeel,
I want the eval to run from files alone with integrity checks,
So that results are trustworthy and reproducible.

**Acceptance Criteria:**

**Given** only `data/` and `results/`
**When** I run eval with the network disabled
**Then** it completes with zero API calls (FR27, AD-9)
**And** it rejects Runs whose `capture_hash` differs from the manifest pin or between systems, Runs with the wrong phase or model, and pages whose ground truth was committed after their first Run
**And** reviewer decisions are never read by eval.

## Epic 6: Freeze, evaluate and report

Fazeel can freeze prompts, run the final Evaluation Run, and produce the A-vs-C table and results note.

### Story 6.1: Prompt Freeze

As Fazeel,
I want a freeze command that tags the repo and checks sources,
So that nothing changes after I see Test results.

**Acceptance Criteria:**

**Given** final Role Specs, Guidance, Worked Examples and Criteria Matrix
**When** I run freeze
**Then** it fails if any Worked Example's `source_page_id` is a `test` or unreviewed page, and Worked Examples are re-sourced from Dev pages (FR10, AD-12)
**And** it writes a git tag and records the Config hash (FR34)
**And** the Criteria Matrix is dated at freeze.

### Story 6.2: Dev versus final model enforcement

As Fazeel,
I want phases and models enforced by code,
So that dev runs never leak into the final table.

**Acceptance Criteria:**

**Given** Config with dev and final model IDs
**When** I start a Run with `phase=dev`
**Then** it uses the dev model on Dev pages only and refuses Test pages (FR33)
**And** an Evaluation Run refuses to start unless every role and the Synthesis Agent use the same final model ID and the freeze tag and Config hash match (FR34).

### Story 6.3: Batch runner and results backup

As Fazeel,
I want one batch command with resume and a backup step,
So that the final run is repeatable and safe.

**Acceptance Criteria:**

**Given** the Page Set and frozen Config
**When** I run the batch command
**Then** it runs A once and C three times per page under one `group_id`, skips Runs whose `run_id` exists, and prints the cost estimate first (FR36, AD-16)
**And** a documented command copies `results/` to a backup before the Evaluation Run
**And** a run stopped at the Cost Cap reports what completed and does not resume without the flag.

### Story 6.4: A-vs-C results table

As Fazeel,
I want one command that writes the comparison table,
So that I can read the numbers.

**Acceptance Criteria:**

**Given** stored Evaluation Runs
**When** I run the table command
**Then** Markdown and CSV tables show A and C metrics from Epic 5 overall and by type, Page Type and Role (FR26)
**And** it reads files only, makes no API call, and states that costs are estimates.

### Story 6.5: Results note against H1

As Fazeel,
I want a results note,
So that supervision and the dissertation have a clear record.

**Acceptance Criteria:**

**Given** the results table
**When** I write the note from the template
**Then** it reports A and C against H1 descriptively and marks the single-agent half untested because System B is deferred (FR26)
**And** it lists at least three concrete lessons for weeks 3-10 including any null result, and states the synthetic-page, builder-labelled and simulated-assistive-technology limits
**And** it lists the open items (Cost Cap value, temperature wording in the proposal).

## Epic 7: Review Screen

Fazeel can read a Report and mark each Issue accepted, rejected or unsure.

### Story 7.1: Show a Report

As Fazeel,
I want a local screen listing a Report's Issues,
So that I can judge each one quickly.

**Acceptance Criteria:**

**Given** a stored Report
**When** I run the review command
**Then** a FastAPI + Jinja server-rendered page lists ranked Issues with element, criterion, Roles, evidence, description, suggested fix, Confidence and a grounded flag (FR28, AD-13)
**And** every screen states the output is guidance, not a compliance certificate (FR30)
**And** the page uses semantic HTML and passes axe-core with no violations.

### Story 7.2: Record decisions

As Fazeel,
I want to mark each Issue accepted, rejected or unsure,
So that my sign-off is saved beside the Report.

**Acceptance Criteria:**

**Given** the review screen
**When** I mark an Issue and save
**Then** the decision is appended to `decisions.jsonl` beside the Report and the Report is unchanged (FR29)
**And** an ungrounded Issue cannot be accepted without an override note
**And** the screen never calls an auditor or an LLM.
