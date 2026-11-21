# Addendum: SystemC_V1 technical how (for architecture and build)

Not requirements. Inputs for `bmad-architecture`. Source: `doc/Proposal_V1.1.pdf`. Revised 2026-11-21.

## Stack
- Python. Playwright for capture; axe-core injected via Playwright (WCAG 2.2 AA tags): it is both **System A** (baseline runner) and a **tool** for the roles that hold it.
- System C: Claude Agent SDK (Python) with subagents. Orchestrator is plain Python.
- Verify Agent SDK option names (agent definitions, allowed tools, hooks) against Anthropic's own documentation before implementation; Proposal V1.1 says so.
- Model: final runs `claude-sonnet-5-5`; dev iteration `claude-haiku-5-5` on the Dev Set only; never mixed in a final run set. Check live pricing before fixing the Cost Cap.
- Scope note: V1 builds System C (template first) and System A. System B (single agent) is a later arm. Keep Issue Schema, post-processing, matching and metrics code system-agnostic so B and real pages plug in unchanged.
- Build order: C template (orchestrator, role specs, schema, hooks, post-processing) -> A runner -> seeded pages + ground truth -> harness -> review screen.

## Repo layout (proposed; Roadmap section 3 is not in the repo)
```text
capture/            Playwright capture, cache, scripted focus trace
agents/             one spec + prompt + examples file per Role, synthesis
baselines/          System A axe-core runner (B later)
tools/              axe runner, contrast calculator, readability scorer, focus-trace reader
orchestrator/       fixed role table, delegation, hooks, validation, post-processing, report
eval/               ground truth, matching rule, metrics, ablation harness
data/pages/seeded/  synthetic pages by page type (ecommerce, gov, forms, content) + manifest
data/pages/real/    later phase: snapshots, terms manifest, site codes
data/ground_truth/  labelled issues (versioned)
results/            JSONL per run and page
config/             model ids, temperature, token caps, loop cap, criteria matrix
```

## Role spec file (example, from Proposal V1.1 section 5.1.1)
```yaml
name: screen_reader
description: Judges the page as a screen-reader user would.
criteria: ["1.1.1", "1.3.1", "1.3.2", "2.4.4", "4.1.2"]
inputs: [accessibility_tree, html, headings, landmarks]
tools: [axe_core]
permissions: read_only
output_schema: issue_v1.json
prompt_file: prompts/screen_reader.md
examples_file: prompts/screen_reader_examples.json   # 3-4 Dev Set examples: clear, clean, borderline
```

## Tools and inputs per role
| Role | Inputs | Tools |
|---|---|---|
| Screen reader | accessibility tree, HTML, headings, landmarks | axe-core |
| Keyboard | focus trace, interactive elements, focus styles | axe-core, focus-trace reader |
| Colour and visual | screenshot, computed styles | contrast calculator |
| Cognitive | layout, instructions, forms, errors | readability scorer |
| Plain language | visible text, labels, links, errors | readability scorer |
| WCAG structure | HTML, ARIA, axe output | axe-core |
| Inclusive design (synthesis) | whole capture + six role outputs | none |

## Hooks
- Post-run: validate output against `issue_v1.json` and evidence present; retry once; second failure logged, role's issues dropped and counted as misses in recall.
- Pre-tool-call: log call (tool, args, role, time) and **block** any tool not on the role's allowlist.

## Orchestrator
```python
ROLES = [
    "screen_reader",
    "keyboard",
    "colour_visual",
    "cognitive",
    "plain_language",
    "wcag_structure",
]


def audit(page):
    capture = load_capture(page)  # cached
    findings = parallel(run_role(r, capture, ROLE_SPEC[r]) for r in ROLES)
    findings.append(run_synthesis(capture, findings))  # after all six finish or fail
    return rank(map_to_wcag(dedupe(findings)))  # deterministic; sets confidence
```

## Issue Schema (draft, revised)
```json
{
  "page_id": "site-a-03",
  "issues": [{
    "element": "css selector or xpath",
    "criterion": "1.1.1",
    "role": "screen_reader",
    "evidence": "alt text is 'image123.png'",
    "description": "...",
    "suggested_fix": "..."
  }]
}
```
After de-duplication each merged issue gains `roles` (list) and `confidence` (integer = number of distinct roles, 1-6, set by code, not by the model).

## Ground truth item (draft)
```json
{
  "page_id": "site-a-03",
  "element": "css selector or xpath",
  "acceptable_criteria": ["2.4.4", "2.4.6"],
  "affected_user_group": "screen_reader",
  "severity": 3,
  "issue_type": "J"
}
```
One item per affected element. Five identical "Click here" links are five items.

## Criteria Matrix
Source: `doc/Proposal_V1.1.pdf` section 5.3 (about 20 draft criteria with R/J/M labels and primary roles; some criteria sit under two roles on purpose). Freeze and date before any Evaluation Run.

## Worked example fixture
Proposal V1.1 section 5.6 table T1-T9 (alt "image123.png" 1.1.1; "Click here" 2.4.4; contrast 2.8:1 1.4.3; placeholder-only label 3.3.2; red-border-only error 1.4.1; "Invalid" message 3.3.3; modal focus 2.4.3; focus behind sticky header 2.4.11; vague headings 2.4.6). Build one Seeded Page that reproduces it and use it as the matching-rule and harness test fixture. Its scoring table uses made-up numbers; do not treat as results.

## Cost calibration
Mishra et al. (2026) Table 6: instrumented workers on 250 page-criterion rows cost USD 36.65 (Gemini 3.1 Pro), 49.71 (Claude Sonnet 5), 64.19 (GPT-5.5). Different workload from V1; use only to sanity-check the Cost Cap.

## Seeded pages (V1)
About 8-10 synthetic pages, one or two per page type: e-commerce (product, cart, checkout form), government and public service (guidance, application form), forms (sign-up, error handling, modal), content and news (article, headings, links). Each has planted defects across R/J/M criteria, clean controls and decoys (decorative icon hidden from AT, correct empty alt, visible focus). Write ground truth in the same commit as the page. If pages are LLM-generated, record the generator model and review every page by hand.

## Real-site candidates (next phase, human-evaluated baseline)
GOV.UK guidance page (OGL, false-positive control); Wikipedia article (CC BY-SA); testing-friendly shop (saucedemo.com or OpenCart demo); optional UAE government portal page; W3C Before and After pages. No commercial news or e-commerce production sites.

## Rejected / deferred
- Criterion-split agents (Mishra): related work, not rebuilt.
- System B build/run and optional B0 no-tools arm: later arms.
- Real and W3C pages, human labelling: next phase.
- Statistical tests, expert kappa, usefulness ratings: dissertation weeks 10+.
- LLM orchestrator: optional later variant, judgemental merging only.
- Packaged skills for role instructions: rejected for reproducibility; plain versioned prompt files.
