# Epic 2 code review (stories 2.2-2.9, commits 40df74b..d17af4d)

Layers: Blind Hunter, Edge Case Hunter, Verification Gap, Acceptance Auditor. Story 2.1 live checks and the
TODO provider terms are known open items, not findings.

## Decisions (resolved)
- Role criteria outside the role's matrix subset: move to `unmapped_issues` (no retry).
- `--resume`: a Cost Cap stop blocks the next audit in that phase until `--resume` is passed.

## Patches (all 21 applied; 288 tests pass, 2 live tests skipped)
1. [high] `run_agent` only catches CostCapReached/RunStopped/ProviderError; a LedgerError or other exception aborts `asyncio.gather` and loses every role. Catch per role -> `failed` (kind `internal`).
2. [medium] Failed attempts are charged to the ledger but missing from `Usage`, `RoleStatus.cost_usd` and `attempts`; tool calls from failed sessions are dropped.
3. [medium] `run_state` returns COMPLETE when every role failed; add FAILED and non-zero exit.
4. [medium] Cost estimate says "at most" but ignores gate and provider retries and the one-session margin and existing ledger spend; show expected and worst case, check against `ledger.remaining()`.
5. [medium] Timeouts are non-retryable; AD-16 says timeout gets bounded retries.
6. [medium] SDK `is_error` retry rule retries deterministic results (error_max_turns); retry only `error_during_execution`.
7. [medium] Merged description/suggested_fix can come from a synthesis echo (sorts first); prefer non-synthesis members.
8. [medium] Role criteria subset enforced only in prompt; out-of-subset criteria go to unmapped (decision above). Synthesis prompt wording fixed (no criteria list, "role reviewers").
9. [medium] `--resume` per-run_id stop never matches a new run; stop becomes per phase ledger, cleared only by `--resume`.
10. [medium] `Run.versions` lacks tool versions (axe-core, Playwright); merge capture manifest versions.
11. [medium] Verification gap: no test of `SdkSessionRunner` without a key (options wiring, error mapping, cost fields); add stubbed-`query` tests.
12. [medium] Verification gap: CLI cost-cap refusal and `--exclude` session count untested.
13. [medium] Two tests depend on the repo `provider_terms.md` staying a TODO template; make them independent.
14. [medium] `visible_text` loses text after removed script/style/hidden nodes (lxml `remove` drops tail); also strip head/noscript.
15. [medium] `criteria_for`: criterion not in matrix plus a valid rule_id goes unmapped; fall through to rule_id.
16. [medium] `parse_output` brace slice breaks on stray braces; use `raw_decode`.
17. [low] `--exclude` accepts any string (traceback); use argparse choices. `--capture-hash` help text wrong.
18. [low] `contrast.failing_rows` ignores NodesKey/unresolved selectors; rgba alpha<1 treated as opaque; sdk_tools handler misses AttributeError; axe_reader nested/missing target.
19. [low] `secrets` ignores `export ` prefix; `terms` rejects `*` bullets and accepts TBD/N/A.
20. [low] `build_axe_rule_map.py` overwrites a frozen matrix; refuse.
21. [low] Cleanups: dead `_ = directory`, string compare of state, vacuous orchestrator invariant check, misplaced `SdkSessionRunner` docstring, `removesuffix` coupling in `synthesis_user_prompt`, "all six roles failed" message when roles were excluded.

## Deferred
- Crashed session leaves a reserve with no settle, shrinking the cap (needs a reconcile tool). Unverified severity: medium.
- Margin of one session budget does not cover six parallel overshoots (AD-8 margin as specified). Unverified: medium.
- Large pages can overflow the prompt; truncation policy belongs with real pages (Epic 6).
- `read_run` puts all System A issues in one bucket; revisit in Epic 3.

## Rejected
- API key read from `.env.systemc` vs AD-16: user-approved deviation; fix would edit the spec.
- `grounded` true for `nodes`: documented decision; fix would edit the spec.
- Synthesis-only confidence 1 vs 0: documented in story 2.8.
- One ledger per phase vs a single ledger: documented decision (settings.toml comment).
- Truncated trailing ledger line, `thinking` hard-coded (only value allowed), stale BUILTIN_TOOLS (tools=[] and hook deny are the guard), non-Latin readability, half-written run dir, synthesis run on zero issues, missing imports in `cli/main.py` (ruff passes), `is_grounded` first-member only (members share one element key), matrix severity default (matrix file has it).
