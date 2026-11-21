# Rubric Review: ARCHITECTURE-SPINE.md vs PRD (SystemC_V1)

Reviewed: 2026-11-21. Spine: `ARCHITECTURE-SPINE.md`. PRD: `prd-SystemC_V1-2026-11-08/prd.md` (revision 2026-11-21).

## Verdict

Strong and mostly enforceable, but not ready to hand down. Three divergence points are left open or ambiguous (severity scale, element normalisation ownership, axe execution/capture identity), and about ten FR consequences have no home in the spine.

## Findings (by severity)

### F1 - HIGH - Severity scale and ranking rule are deferred, but two units must agree on them
- Deferred says "Ranking rule details and severity scale: documented in `postprocess/rank.py` during build".
- `GroundTruthItem.severity` is authored in `data/ground_truth/` (AD-12/AD-14, page generation). `postprocess/rank.py` assigns severity and rank. FR-20 correlates one against the other (Spearman, P@10).
- Nothing fixes the scale, ordinal vs numeric, or how a tie is broken. Ground truth and postprocess can diverge, and ground truth is committed before any Run, so a late fix means re-labelling.
- Fix: put the severity enum and the rank formula inputs in `contract/`, as an AD.

### F2 - HIGH - Element normalisation has no owning module and no allowed dependency path
- AD-10 (dedupe, `grounded`) and AD-11 (matching, CSS vs XPath) both need "resolve selector to canonical node path in Capture HTML".
- `postprocess` and `eval` may import only `contract` and `store`, and `eval` never imports `postprocess`. `tools` is not importable from either. The HTML-parsing resolver therefore has no declared home.
- Likely outcome: two implementations. That is the "different matching rule per system / double counting" divergence AD-10/11 claim to prevent.
- Ground-truth locators are authored by hand or generator, and nothing says they are normalised with the same function.
- Fix: name one pure module (for example `contract.element` or `tools.element_path`), add the edges to the graph, and add a test that GT locator, agent output and postprocess agree.

### F3 - HIGH - Where axe runs, and which Capture is "the" Capture, are ambiguous
- axe-core needs a live DOM. `tools/` is "pure functions over a Capture" and the Capture artefact list has no axe result.
  - It is unstated whether axe re-opens the saved HTML in a browser (loses external resources, so results may differ from capture time) or runs at Capture time.
  - System A (FR-37/38 determinism) and the Role-agent axe tool (FR-11) could return different results.
- `{capture_hash}` is content-addressed but `capture.json` holds timestamps and versions, and screenshots are non-deterministic.
  - A re-capture can yield a second hash for the same page.
  - No rule pins one capture per `page_id` for A and C ("Single input", PRD §5), nor says what happens on re-capture.
- The FR-6 "zero network requests" check has no named test.

### F4 - MEDIUM - Failure and budget semantics have gaps
- AD-6 and AD-4 define failure only for the six roles.
  - Synthesis failure is undefined: does the Run continue, and what is `role_status` for it?
  - It is unclear whether synthesis receives validated or raw role output, and whether it receives a failed role's output.
- Cost cap (AD-8): six sessions start in parallel, each with `max_budget_usd` = "remaining cap share".
  - "Share" is undefined. In-flight sessions finish after the cap is hit, so overshoot is unbounded by rule.
  - Resume after `stopped_cost_cap` is unspecified. PRD UJ-1 says "does not resume silently".
- Ablation runner (Deferred) removes a role while AD-4 says the table is fixed and AD-6/AD-11 treat a missing role as FN.
  - Ablation runs would collide with the `results/{system}/...` layout and be scored as failures.
  - Needs at least a `system` id or variant field now.
- AD-1 says metrics accept only `AuditResult`/`Report`, but AD-11 says metrics consume `Report` and GT only. Role status and usage live in `AuditResult`/`Run`. Pick one.

### F5 - MEDIUM - PRD FRs and consequences with no spine home

Every FR has a package in the map, but these specific requirements are not carried by any AD, contract field or deferral note:

| FR | Gap |
| --- | --- |
| FR-7 | Polite capture / robots.txt: neither built nor listed in Deferred (only "redaction and terms tooling"). |
| FR-8 | Test that a role is never skipped, added or called twice is absent from Tests convention. |
| FR-10 | Example count and prompt-size tokens per Role reported: no owner. |
| FR-12 | Seconds per Page (parallel stage and whole Run): not in `AuditResult` or Run fields. |
| FR-14 | Synthesis "priority statements" distinct from Issues: no contract type. |
| FR-18 | "What the system cannot test" statement in Report JSON: only the review-screen guidance line (AD-13) is covered. |
| FR-21 | Ground truth must also record Criteria with no issue per Page: `GroundTruthItem` has no page-level field. |
| FR-24 | Run-to-run agreement over 3 Runs: no definition or location. |
| FR-35 | Provider-terms gate ("first LLM Run refuses to start without record"): only a file name in the deployment paragraph, no enforcing rule. |
| FR-37 | Axe "needs review" results stored separately: not in `AuditResult`. |
| NFR | Quality targets (95%/90%), under 5 min per page, prompt caching: unmentioned (the first is partly measured by AD-6). |

Contradiction with the PRD: FR-31 and §5 say fixed temperature and a token cap. AD-7 says the SDK cannot pin them. This is a justified deviation, but the PRD should be amended, or the PRD NFR will read as violated.

### F6 - MEDIUM - Config layer undefined; dimension gaps
- AD-7 and Conventions require `config.load()`, but no `config` package appears in the layer table or dependency graph (only `config/` data). Imports of Config by `auditors`, `postprocess` and `cli` are unspecified.
- Provider strategy covers one provider only. Missing: API error handling distinct from validation retry (429, 5xx, timeouts); role timeout value; concurrency limit across pages; model deprecation. Errors convention covers typed exceptions but not transient-failure policy.
- Operations: `results/` and `data/captures/` are git-ignored, yet they are the dissertation evidence. No backup or retention, no batch runner for 10 pages x 3 runs, no resume semantics.
- API key: environment only, which is correct. Missing: `.gitignore`/secret-scan guard, logging redaction rule (hash of args is good), and the note that the SDK/CLI subprocess also reads the key, which conflicts with "no module reads env vars except in `auditors`".
- Stack pins are unconfirmed ("seen"), which is acknowledged. Low severity; must be closed before build.

## Checklist results

| Criterion | Result |
| --- | --- |
| Fixes the real divergence points, misses none | Partial. Misses F1, F2, F3. Strong on Issue contract, auditor port, tool allowlist, cost ledger, freeze, dev/test separation. |
| Every AD Rule enforceable and prevents its divergence | Mostly. AD-2, 3 (store-only reads), 5, 7, 12 are testable. Weak: AD-3 "no network request" (no test named), AD-8 "remaining cap share", AD-9 "never rewritten" (only `store` enforces; say so), AD-10/11 (F2). |
| Nothing in Deferred lets units diverge | No. Severity scale and ablation shape can diverge (F1, F4). Others (System B, real pages, stats, sampling, cost cap value) are safe. |
| Covers every PRD feature/FR | No. Uncovered or partly covered: FR-7, FR-8 (test), FR-10 (reporting), FR-12 (timing), FR-14 (priority notes), FR-18 (statement), FR-21 (no-issue criteria), FR-24 (agreement), FR-35 (gate), FR-37 (needs-review). SM-1..SM-7 are bound but SM-3's "A recovers 90% of R-type" has no test home. |
| No dimension silently skipped | Deployment and environments: covered. Provider strategy: thin (F6). Operations: thin (F6). API key security: minimal (F6). Error handling: partial (F4, F6). |

## What is good (no action)
- Clear layer and dependency rules, one Issue contract with code-set fields, immutable Captures, hook-enforced allowlist (correctly noting `allowed_tools` only auto-approves), failed roles scored as FN, pure postprocess shared by A and C, and files as the database with a ground-truth-before-run check.
