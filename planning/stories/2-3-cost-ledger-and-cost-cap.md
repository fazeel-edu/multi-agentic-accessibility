---
title: 'Story 2.3: Cost ledger and Cost Cap'
type: 'feature'
created: '2026-11-21'
status: 'in-review'
route: 'dispatch'
---

Acceptance criteria: `planning/epics.md` Story 2.3.

## Implementation Notes

- `store/ledger.py`: append-only JSONL under an `fcntl` file lock. `reserve` before a session, `settle` with the LAST cumulative `total_cost_usd` and `model_usage` (`last_result_cost` never sums). A reservation must leave a margin of one session budget under the cap; otherwise the Run is marked stopped, no new session starts, and settling in-flight sessions still works.
- A stopped Run raises `RunStopped` on the next reserve unless `allow_resume=True` (explicit flag; recorded as a `resume` event); the cap still applies after resuming.
- `estimate_cost` and `CostEstimate.describe()` give the upper bound to print before any LLM stage, labelled an SDK estimate.
- One ledger per phase (`results/ledger-dev.jsonl`, `ledger-eval.jsonl`) so dev iteration cannot use the evaluation budget; `Ledger.for_phase` takes values from Config. Parallel-reservation test: 40 threads, exactly 9 granted at cap 10.
- Wiring into the orchestrator and CLI flag is Story 2.6 and 2.9.
