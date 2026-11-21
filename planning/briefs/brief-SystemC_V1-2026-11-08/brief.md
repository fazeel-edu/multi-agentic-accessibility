---
title: "Product Brief: SystemC_V1"
status: final
created: 2026-11-08
updated: 2026-11-21
---

# Product Brief: SystemC_V1

Source of truth: `doc/Proposal_V1.1.pdf` (latest). Related work: `doc/SystemB.pdf` (Mishra et al., 2026). This revision supersedes the 2026-11-08 version, which was built from Proposal v2 and a Roadmap.

## Executive Summary

Rule-based checkers such as axe-core test web accessibility fast and repeatably, but they reach only part of WCAG. Many barriers need judgement: an image whose alt text is "image123.png", confusing wording, poor reading order, weak focus handling, cognitive overload. Language models can judge these, but a recent criterion-split LLM system (Mishra et al., 2026) reached 86% recall at only 56% precision on 250 page-criterion records (axe-core: 36% recall, 90% precision; uncued vision-language model: 67% / 61%). Breadth came with many false alarms. No study tests a split **by user role**.

SystemC_V1 is a one-week, end-to-end Python prototype of the MSc project's **System C**: a deterministic orchestrator sends one captured web page to six role agents in parallel (screen reader, keyboard, colour and visual, cognitive, plain language, WCAG structure), then to an inclusive-design synthesis agent, and merges the findings into one ranked, evidence-backed report. V1 builds **System C (the template, built first) and System A (axe-core baseline)**. System B (single LLM agent) is deferred to a later arm; V1 keeps the Issue Schema, post-processing and matching rule compatible with it.

V1 runs on **synthetic pages only**: Fazeel builds pages for each page type (e-commerce, government and public service, forms, content and news) with planted accessibility issues, clean controls and decoys, so ground truth is known by construction. A and C are then checked quickly on them. Real public pages and human-evaluated pages come next, as the baseline set, through the same harness.

The week's output is a working System C pipeline, a reusable evaluation harness, and the first honest numbers for A and C (precision, recall, F1, cost, time, agent behaviour) on the synthetic set. Those numbers show the pipeline works; they are optimistic by design and are not dissertation results. It is dissertation evidence: a de-risked build before the formal 25-30 page, expert-checked evaluation.

## The Problem

An accessibility auditor today picks between fast, narrow automation and slow, variable expert review. Vigo et al. (2013) found automated tools cover at most 50% of success criteria; Brajnik et al. (2011) found non-expert judges drop in validity and reliability. LLM auditors widen coverage but, unverified, flood reviewers with false positives.

For this project the immediate problem is different: Fazeel has a 12-week dissertation plan whose riskiest parts (agent design, evaluation harness, cost, run-to-run variance, ground-truth labelling) only surface when the system exists. Waiting until weeks 5-10 to find that out is the schedule risk.

## Research Question and Hypothesis

**Question (Proposal V1.1 section 7).** Can a role-based multi-agent system find more real accessibility problems in web interfaces than a single automated checker or a single LLM agent, and at what cost in false alarms? V1 measures System C's side of the sub-questions: (1) detection (precision, recall, F1); (2) issue type (does value concentrate on judgement-based criteria); (3) role value (which roles add issues); (4) quality and cost (ranking, cost per page and per true positive).

**Hypothesis H1 (section 6.6).** On the same pages and ground truth, C has higher recall than axe-core and than a single agent, with precision no more than 10 percentage points below the single agent; the gain is largest on judgement-based criteria. V1 measures the axe-core half of H1 directly (A vs C, same pages and ground truth, synthetic set). It has no System B, so the single-agent half is reported as not yet tested. Everything is reported **descriptively**, and flags which parts only the full evaluation on real pages can answer. H1 holding is not a V1 success criterion; a null result is a valid finding.

## The Solution

Build order: System C template first (orchestrator, role specs, schema, hooks, post-processing), then System A, seeded pages with ground truth, harness, review screen. System A runs axe-core with WCAG 2.2 AA tags on the same capture, with no LLM, and its violations go through the same schema and post-processing.

A pipeline: **capture** (Playwright: HTML, computed styles, accessibility tree, screenshot, scripted keyboard focus trace; cached) then **analyse** (six role agents in parallel, then the synthesis agent) then **orchestrate** (deterministic Python: de-duplicate by element and criterion, map to WCAG, score severity, rank, set confidence) then **report** (structured JSON plus a minimal review screen).

Design rules from Proposal V1.1 section 5:
- **Orchestrator is ordinary code, not an LLM.** "Choosing the role" is a lookup in a fixed table: same decomposition for every page, no routing variance, no skipped role. An LLM orchestrator is an optional later variant limited to judgemental merging.
- **Role agents inherit nothing.** Each gets only its capture slice, criteria subset, allowed tools, output schema, guidance and 3-4 worked examples (a clear issue, a clean case, a borderline case). Examples come from the Dev Set only and are fixed and dated before any evaluation run.
- **One versioned spec file per role** (role prompt, criteria subset, input artefacts, tool allowlist, output schema, examples). Plain prompt files, not packaged skills, so every run is reproducible and citable.
- **Least tools, enforced.** Tools per role: axe-core, contrast calculator, readability scorer, focus-trace reader. Roles are read-only: no file writes, shell, network or browser control. A pre-tool hook logs each call and blocks anything off the allowlist (Mishra et al. found their declared tool list was guidance, not an enforced boundary).
- **Structured output with a gate.** One JSON issue schema; a post-run hook rejects malformed or evidence-free issues and retries once. Role failure is isolated: one bad role does not spoil the others.
- **Confidence flag** = number of distinct roles reporting the same element and criterion (1-6). A signal, not proof.
- Built with the Claude Agent SDK and Claude models; prompts, model IDs and settings under version control; the Agent SDK exposes no temperature, so run-to-run variance is measured, not pinned. The tool gives guidance, not compliance certification.

## What Makes This Different

- **Role split, not criterion split.** Fixed 6+1 agents regardless of criteria count; cost scales with roles. Mishra et al. assign one agent per WCAG requirement (40 agents).
- **Overlap on purpose.** Roles share some criteria (for example 2.4.4 under screen reader and plain language); the orchestrator removes duplicates, and the synthesis agent can spot patterns no single role owns (five identical "Click here" links defeat a list of links).
- **Hypothesised benefits, each tied to a V1 measure:** focused context (precision), specialised instructions (per-role recall), tool restriction (tool-call logs), parallelism (seconds per page), failure isolation (schema-valid rate per role), attribution (role-removal ablation), cross-checking (confidence vs precision), synthesis (issues found only by the synthesis agent). These are claims to test, not results.
- **Honest by design.** Precision, grounding rate and cost per true positive are reported next to recall; a null result is a valid result.
- No technical moat is claimed. The edge is a controlled design and speed of getting evidence. V1 does not test role split against criterion split (no criterion-split system is built).

## Who This Serves

- **Primary: Fazeel (MSc AI student, builder, researcher and V1 reviewer).** Needs a working harness and early metrics to steer weeks 3-10, and material for supervisor meetings.
- **Secondary: supervisor and future reviewers.** Need a reproducible, clearly bounded artefact. [ASSUMPTION: supervisor sees V1 results, not necessarily the code.]
- **Downstream: human accessibility reviewer.** In V1 the reviewer is Fazeel; V1 involves no human participants, so no external expert is contacted. Expert audits and Cohen's kappa stay in the dissertation, after ethics approval and consent.

## Success Criteria

"Done" means System C runs end to end and the numbers are trustworthy, not that C wins.

1. System A (once) and System C (3 runs) run on every V1 page and write JSONL results per run and page.
2. Seeded pages have exact, versioned ground truth, committed before any system output exists; the matching rule (same element, any acceptable criterion; repeated problems count once per element) is written and unit-tested, including the T1-T9 example page from Proposal V1.1 section 5.6. System A recovers at least 90% of planted rule-checkable defects (harness sanity).
3. Report for A and C: precision, recall, F1 overall and by issue type (R/J/M) and page type; for C also tokens, cost and seconds per page, and cost per true positive.
4. Report ranking quality for A and C (precision at top 10, Spearman against Fazeel's severity labels), WCAG coverage (share of in-scope criterion-page pairs correctly flagged, or correctly reported empty), and confidence vs precision (precision of issues reported by 1, 2, 3 or more roles).
5. Report agent behaviour: schema-valid rate, evidence-present rate, grounding rate, run-to-run agreement over 3 runs, per-role recall and unique contribution, issues found only by the synthesis agent. A failed or dropped role counts as missed issues, and failures are reported separately.
6. Total API spend stays under the cap. [ASSUMPTION: about USD 50 for the week, hard stop in code, to be confirmed. Mishra et al. report USD 37-65 for a full 250-row worker run on a frontier model, so the cap may be tight; check live pricing first.]
7. Results are logged in a short note that reports C against H1 descriptively, including any null or negative outcome.

## Scope

**In (V1, 7 days):**
- Capture and cache (scripted focus trace, identical steps for every page); System C: orchestrator, six role agents and synthesis agent (built first, as the template); System A (axe-core, WCAG 2.2 AA tags); role spec files, guidance and Dev Set examples; schema validation with one retry; allowlist and validation hooks; deterministic post-processing; JSON report and a minimal review screen for Fazeel; evaluation harness with the metrics above; role-removal ablation (including removing the synthesis agent) if time allows.
- Page types (Proposal V1.1 section 6.1): e-commerce, government and public service, forms, content and news; mobile-sized variant only if time allows.
- **Pages: synthetic only** [ASSUMPTION: about 8-10 seeded local pages]. One or more per page type, with planted defects across the 20 draft criteria (R, J and M), clean controls and decoys (for example a decorative icon correctly hidden) so false positives are measurable. One page reproduces the T1-T9 example page. Ground truth is written with each page, before any system output. A few pages are the Dev Set (guidance, examples, prompt tuning); the rest are the Test Set.
- English, left-to-right pages only. Right-to-left and other scripts are out of scope, stated as a limit (decision to confirm with the supervisor).
- Before the first LLM run, read the model provider's terms on data retention, training use and zero-retention, and record the date. Synthetic pages contain no third-party or personal data.

**Out of V1 (next phase, same harness):** real public pages (GOV.UK guidance, Wikipedia, a testing-friendly shop, optional UAE portal page) and W3C Before and After pages, with page-terms table, robots.txt and redaction checks, human WCAG-EM labelling and site codes; these become the human-evaluated baseline set. **Later in the dissertation:** System B (single agent, same tools, guidance, model and post-processing as C) and optional B0 no-tools arm; literature review; ethics application; expert recruitment and Cohen's kappa; usefulness ratings; the full 25-30 page set and licence table; Wilcoxon, effect sizes and bootstrap intervals; optional Mishra external check; native mobile apps; time-based media (WCAG 1.2.x); any compliance certification.

**Known limit:** synthetic pages and their ground truth are made by the same person who writes the prompts, and planted defects are usually cleaner than real ones. V1 numbers are optimistic and indicative only; they show the pipeline works, not how C performs on real sites. V1's Prompt Freeze is a prototype freeze; the dissertation system is frozen at the end of week 9.

## Decisions

- **Model.** Final C runs use `claude-sonnet-5-5` for all six roles and the synthesis agent, with pinned effort, loop cap and per-session budget (the Agent SDK cannot set temperature or max_tokens; defaults are a stated limit). `claude-haiku-5-5` is for dev iteration on the Dev Set only. Models are never mixed inside a final run set. Live pricing is checked in the architecture step to set the hard cost cap.
- **Scope.** V1 builds System C (template first) and System A; System B is deferred (decision 2026-11-21).
- **Pages.** V1 uses synthetic seeded pages only; real and human-evaluated pages follow as the baseline set (decision 2026-11-21).
- **Page production.** Seeded pages are LLM-generated, then reviewed by hand, with the generator model recorded per page; the generator may share biases with the audit model, so prefer a different one.
- **Reviewer.** Fazeel reviews V1 reports; no external participants.
- **Hypothesis.** H1 is reported against, not a gate.

## Risks and Open Questions

- **Cost.** Three runs of seven agents per page can exhaust the cap. Mitigate: cache captures, cap tokens, develop on one seeded page first.
- **Label leakage.** Write ground truth with each page before any system output; examples and guidance from Dev Set pages only.
- **Synthetic optimism.** Builder-written pages and ground truth are easier than real sites and may share assumptions with the prompts. Mitigate: decoys and clean controls, and treat results as a pipeline check until real pages are added.
- **Simulated assistive technology.** Role agents use the accessibility tree and a scripted focus trace, not real assistive technology or live browsing.
- **No single-agent baseline in V1.** The B half of H1 waits for System B; A vs C stands on the synthetic set only.
- **Open.** Confirm the cost cap, the seeded page list and Dev/Test split, and RTL scope with the supervisor.

## Vision

If V1 shows the pipeline works and the role split is promising (or clearly not), the same harness extends in weeks 5-10 with real, human-evaluated pages, the single-agent baseline (System B), the full 25-30 page expert-checked evaluation, ablation and statistics. If it works, a role-based auditor could become a reusable reviewer-assist tool; if not, V1 gives an explained null result worth reporting.
