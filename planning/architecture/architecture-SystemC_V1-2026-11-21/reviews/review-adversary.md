# Adversarial review: ARCHITECTURE-SPINE.md (SystemC_V1)

Method: for each finding, two units one level down that each obey every AD literally yet build incompatibly. Each ends with a proposed AD fix.

Verdict: NOT READY as a build substrate. The layer/port structure is sound, but the shared-data shapes the units meet at (element identity, GroundTruthItem, Report vs AuditResult, criterion mapping, the Capture's contents) are named but not defined. Eight holes below; F1-F5 would cause silent wrong metrics, not crashes.

---

## F1 (critical) Element normalisation has no single owner or algorithm

Pair: `postprocess` dev vs `eval` dev (and the ground-truth author).
- AD-10: postprocess normalises "by resolving to a node in the Capture HTML and using a canonical node path". AD-11: eval matches "same normalised element". The dependency graph forbids `eval -> postprocess` (eval imports only contract and store), so eval cannot call postprocess's normaliser. Each dev writes their own, both "to the letter".
- "Canonical node path" is unspecified: nth-child vs nth-of-type, whether text/comment nodes count, parsed from stored source HTML vs the serialized post-JS DOM (Playwright DOM and a Python parser such as lxml/bs4 disagree on implicit tbody, whitespace nodes, and tag recovery), id-based shortcut vs positional.
- GroundTruthItem.element is authored by hand (or by the generator, AD-14) at page-design time. Nothing says it is resolved against the Capture, so GT may hold a CSS selector while Reports hold a path. Match never fires; recall reads near zero for both systems.
- axe returns selector arrays (iframe and shadow-DOM `["#host", "button"]`) and multiple nodes per violation. Agents return free-form CSS, sometimes just visible text. One Issue to many nodes, or one node to many Issues, is undefined.
- Unresolvable selector: `grounded=false`, but what is the dedupe key? Two different hallucinated selectors with the same criterion may merge or not, depending on the dev.
- Issues about absence or page-level scope (no skip link, missing `lang`, reading level, heading order across the page) have no element at all.

Fix, new AD-15 "Element identity":
- One function `tools/element.py::element_key(html, selector) -> ElementKey | None`, pure, imported by postprocess, eval, and the GT binder (allowed edge: eval -> tools, add to the graph).
- Fixed algorithm: parse the Capture's stored serialized DOM (Playwright `page.content()` after settle) with one named parser; path = tag + nth-of-type chain from `html`, ids ignored; one test vector file shared by all.
- `Issue.element` stays agent text; `Issue.element_key`, `GroundTruthItem.element_key` and `MergedIssue.element_key` are set by code only. A `cli bind-gt` step resolves every GT item against the pinned Capture and fails if any does not resolve. eval compares keys only.
- `ElementKey` is a tagged union: `node(path)`, `nodes(paths[])` (multi-node GT/axe: match if any hit, count once), `page` (scope-level; criterion-only match), `unresolved(sha of raw selector)`. Dedupe and match behaviour for each variant is stated in AD-10/AD-11.

## F2 (critical) GroundTruthItem and the failed-role-is-FN rule are not implementable

Pair: `eval` dev vs `role_auditor` dev / `postprocess` dev.
- AD-11 says a failed role "leaves its items as FN". That needs each GT item to say which role is responsible for it. GroundTruthItem has no defined fields: no `acceptable_criteria[]`, `type`, `page_type`, `responsible_roles[]`, `severity`, `scope`. A GT item may be catchable by several roles; "role failed so FN" is then wrong when another role still hits it.
- Further, AD-6 says the failed role's issues are dropped, which already makes them FN by absence. The two statements are redundant or contradictory, and `postprocess.run(raw_issues, capture, matrix)` never receives `role_status`, so Report cannot carry it; AD-1 puts role_status in AuditResult, AD-11 says metrics consume only Report and GT. eval has no legal source for role_status.
- Role-scoped metrics (AD-11) need the GT-to-role relation; ablation (removing a role) needs it too.

Fix, tighten AD-2 and AD-11:
- Specify GroundTruthItem fields in the AD (id, element_key, acceptable_criteria[], issue_type, page_type, expected_roles[], scope, severity, status). `expected_roles` is attribution for scoped metrics only; overall TP/FN never depends on role_status.
- `Report` embeds `run_id, system, phase, capture_hash, config_hash, role_status{}`; `postprocess.run(audit_result, capture, matrix)` takes the whole AuditResult, not raw_issues. Delete "failed role leaves items as FN" in favour of: "a GT item is TP iff matched; failed roles only affect role-scoped metrics and the failed-role count".

## F3 (high) Who maps axe rules to criteria, and are roles/criteria one vocabulary?

Pair: `axe_auditor` dev vs `postprocess` dev (the "map" step).
- AD-1 requires raw_issues in contract shape with `criterion` a dotted string. AD-10 lists "dedupe, map, score, rank" in postprocess. axe_auditor dev maps rule id to SC to satisfy AD-1; postprocess dev maps again (or maps only if criterion is missing). Both comply. One axe rule maps to 0..n SC (best-practice rules have none; `aria-*` rules map to several), so dedupe on `(element, criterion)` yields different counts depending on which map ran first.
- `role: axe_core` is not in the Naming role ids; the Issue.role enum is undefined for axe and for synthesis. The conventions list seven role ids while AD-4 says six roles plus synthesis. Synthesis issues carry which `role`? If synthesis re-emits a role's finding under `synthesis`, `confidence = len(roles)` counts it as an independent voter, inflating confidence and double-counting in role-scoped metrics.

Fix, new AD-16 "Criterion mapping and role vocabulary":
- The axe-rule-to-SC table lives in `config/` Criteria Matrix, applied only in `postprocess` (the one "map" owner); adapters emit native identifiers (`rule_id` field on Issue, `criterion` nullable). One axe rule with n SC expands to n Issues in postprocess, deterministically; rules with no SC get criterion `null` and `best-practice` and are reported but not scored as WCAG hits.
- `Role` is a closed enum in `contract/` with explicit members: the roles table (fix 6 vs 7), `axe_core`, `synthesis`. Synthesis issues carry `origin=synthesis` and a mandatory `derived_from[role]`; they add their derived roles to `roles` rather than a new voter, and never raise confidence on their own.

## F4 (high) Report, Run and decisions have unclear ownership and mutation paths

Pair: `cli`/`store` dev vs `postprocess` dev vs `review` dev.
- AD-9: "Runs and Reports are append-only", yet the layout only defines `results/.../{run_id}.jsonl + run.json`. Where is the Report written, by whom (postprocess is pure), under what name? Rank/severity rules are "documented during build" and may change; the Report is derived. Dev A regenerates Reports over old Runs (overwrite), dev B writes `report-2.json`; both obey AD-9 depending on reading.
- `decisions.json` is written "beside" the Report by review, but review, store, and the append-only rule collide: decisions are mutable (user can change their mind). Does eval read decisions (e.g. to treat accepted ungrounded issues as TP)? Unspecified; one dev has eval ignore them, another folds them in.
- Multiple Runs per page (3-run agreement design): who aggregates, and by which key? run_id embeds a timestamp, so "the same Run" for agreement is ambiguous.
- Ledger: AD-8 says single writer, but sessions are concurrent asyncio tasks and several CLI processes may run (dev and eval); no locking or file format stated; "remaining cap share" per session is racy.

Fix, tighten AD-9 and AD-8:
- Name the files: `run.json` (AuditResult, immutable), `report.{postprocess_version}.json` (derived, regenerable, keyed by postprocess version/hash, never edited in place), `decisions.jsonl` (append-only events with timestamps; latest-wins view computed on read). State that eval never reads decisions.
- Add `Run.group_id` (page, system, config_hash, phase) for the N-run design; agreement and means aggregate over `group_id` in one eval function.
- Ledger: an append-only JSONL with an atomic append and a file lock; reserve-then-settle (`reserve(usd)` before session start, `settle(actual)` after) inside one asyncio lock; a second process refuses to start while the lock is held.

## F5 (high) Capture contents and axe/contrast ownership; systems may see different captures

Pair: `capture` dev vs `tools/axe` dev vs `axe_auditor` dev; and A-vs-C comparison.
- axe-core needs a live DOM and JS execution. AD-3 forbids network after Capture; "tools: axe" is in the pure-tools layer and `tools` "never open files directly". Dev 1 has `capture` run axe and store JSON (Capture contains it, per `capture.json` tool versions). Dev 2 implements `tools/axe` that re-runs axe via a fresh headless browser on stored HTML (no network, "pure"). Results differ (viewport, fonts, scroll state, post-hydration DOM). `axe_auditor` and the role tool "axe" (System C screen_reader etc.) could then see different axe output.
- "Pure functions over a Capture" and "tools -> store" conflict: either tools take parsed Capture objects (then who loads) or call store.
- `capture_hash` content-addressed: what is hashed? Screenshots and timestamps are nondeterministic, so recapturing the same page produces a different hash and a second directory. Nothing pins which capture a page uses; A and C could run on different captures of one page; eval joins on `page_id`; GT binding (F1) is relative to one of them.

Fix, new AD-17 "Capture manifest and pinned capture":
- `capture.json` enumerates every derived artifact, including `axe_results.json` (run once, at capture time, with the vendored axe), contrast table, focus trace. `tools/*` are pure functions of a loaded `Capture` object; `store.load_capture()` is the only loader. No tool runs a browser.
- `capture_hash` = hash over a stated list of deterministic inputs (serialized DOM, computed-style dump, a11y tree, axe_results, focus trace), excluding screenshot and timestamps.
- `data/pages/manifest.json` pins exactly one `capture_hash` per page; auditors, GT binding and eval all read the pin; eval refuses runs whose `capture_hash` differs from the pin or between systems.

## F6 (medium) Issue contract leaves agent-vs-code fields ambiguous in two directions

Pair: `role_auditor` dev vs `contract` dev.
- AD-2: agents set `element, criterion, role, evidence, description, suggested_fix`. `role` is set by the agent, yet AD-10 treats `roles` as code-derived and an agent can write any role id (or someone else's). The orchestrator fills `role` per session (safer) or trusts the agent; both literal.
- `evidence` is only "non-empty" (AD-6): a dev can validate non-empty string; another requires a quoted substring of the Capture. Hallucination filtering differs by system (axe evidence is a node snippet).
- `criterion` freeform dotted string: "2.4.11" vs "2.4.11 Focus Not Obscured" vs WCAG 2.1 vs 2.2 numbering; the Matrix version is not pinned in the contract.
- No `Issue.id`, so matching duplicates and the review screen cannot reference an Issue stably; the "surplus matches counted as duplicates" metric needs a stable merge identity.

Fix, tighten AD-2/AD-6: `role` is code-assigned by the orchestrator (agents do not emit it); `criterion` must be a member of the Criteria Matrix id set, validated by the output gate (invalid = gate failure); `evidence` must be a verbatim substring or node reference resolvable in the Capture (shared validator in `contract`-adjacent `tools`); `Issue.issue_id` is a code-assigned hash of `(system, run_id, element_key, criterion, ordinal)`; `wcag_version` stored in Criteria Matrix and Report.

## F7 (medium) Dependency and purity rules contradict the layer table

- `postprocess` and `eval` are "pure over files" but `postprocess` reads the Capture (resolving elements) while its graph edge is only `-> contract`; it has no `store` or `tools` edge, so the Capture must be passed in as an object; AD-10 passes `capture`. Who loads it, and with what type? Add the type `contract.Capture` (loaded) vs `CaptureManifest` (on-disk) explicitly.
- `config.load()` is the only config reader but `config/` is a data directory, not a package in the layer table; unclear whether it lives in `contract`, `store`, or its own module and where Role Spec/Matrix models are defined (contract says "Config" model exists). Two devs create `config.load()` in two places.
- `auditors/role_auditor/sdk_tools` read Capture "through store" while AD-5 says tools return text/JSON to the model; truncation/size limits of tool outputs are unspecified, so System C's effective evidence differs from System A's input (the fairness of comparison). Not an incompatibility between units but an unstated shared limit.

Fix: add a Module Interfaces table (loader types, who calls whom), put `config.load()` in `store` returning `contract.Config`, and a `tool_output_limit` pinned in config.

## F8 (low) Ids, naming and phase semantics

- `run_id = {system}-{UTC timestamp}-{n}`; `n` undefined (per second? per page? per group). Two concurrent CLIs collide.
- System id `axe` vs role id `axe_core` vs module `axe_auditor`: three spellings; results dir uses system ids, role_status uses role ids; the JSON key vocabulary will drift.
- `phase` is on Run but `dev`/`test` page split is on manifest; eval's "phase=eval on test pages" check is split between two sources; dev pages may be run with phase=eval by mistake and silently excluded or included.

Fix: define id grammar regexes in `contract`, one enum for system ids, and have `store` refuse to write a Run whose (phase, page split, model) combination is invalid.

---

## Summary table

| # | Pair | Failure | Fix |
| --- | --- | --- | --- |
| F1 | postprocess / eval / GT | different element keys, near-zero recall | AD-15 shared `element_key`, GT bound to pinned Capture |
| F2 | eval / role_auditor / postprocess | no GT fields, role_status unreachable | full GroundTruthItem and Report fields; postprocess takes AuditResult |
| F3 | axe_auditor / postprocess | double mapping, role enum gaps, synthesis inflating confidence | AD-16 |
| F4 | store / review / cli | Report/decision mutation, ledger races | named files, append-only decisions, locked ledger |
| F5 | capture / tools / axe_auditor | axe run twice, different captures | AD-17 capture manifest and pin |
| F6 | role_auditor / contract | role, evidence, criterion semantics | code-set role, validated criterion/evidence |
| F7 | module graph | purity/loader contradictions | interfaces table |
| F8 | ids | collisions | id grammar |
