# Review: versions and SDK claims (ARCHITECTURE-SPINE.md)

Reviewed 2026-11-21. Method: PyPI/npm registry JSON (live), code.claude.com Agent SDK docs (python, hooks, custom-tools, permissions), platform.claude.com model overview and task-budgets pages, claude-agent-sdk-python CHANGELOG on GitHub.

## Verdict

Architecture is sound and most claims hold, but the spine is **not yet build-ready**: versions are stale, and three SDK claims are wrong or unconfirmed (AD-5 `tools` semantics, AD-7/AD-8 `task_budget`, AD-7 `thinking`). The "seen, unconfirmed" Stack table was never closed; this review closes it.

## 1. Versions (live registry, 2026-11-21)

| Package | Spine says | Current | Action |
| --- | --- | --- | --- |
| claude-agent-sdk | 0.2.143 (seen) | **0.2.187** (2026-11-20); requires Python >=3.10 | Pin 0.2.187; need >=0.2.177 for `on_failure="block"` (see F2) |
| playwright (Python) | 1.65 | **1.65.2** (2026-11-14); Python >=3.10 | Pin 1.65.2 |
| axe-core (npm) | 4.12-4.14 | **4.14.1** (2026-11-16), license MPL-2.0 | Pin exact 4.14.1; note MPL-2.0 when vendoring `axe.min.js` |
| pydantic | 2.14.0 | **2.14.4** | Pin 2.14.4 |
| FastAPI | 0.162.7 | **0.165.0** (Python >=3.11) | Pin 0.165.0 |
| Jinja2 | unversioned | 3.1.6 | Pin |
| Python | 3.12+ | FastAPI needs >=3.11; SDK >=3.10 | OK |

All named technologies exist and fit. pytest, ruff, uv not checked (unpinned "latest"); pin at build.

## 2. SDK claims against official docs

| Claim | Status | Evidence |
| --- | --- | --- |
| `setting_sources=[]` isolates sessions | **Confirmed.** `[]` disables user/project/local. Min version ">=0.1.60" also confirmed (CHANGELOG 0.1.60: fixed `[]` being dropped as falsy). | python ref; CHANGELOG |
| `create_sdk_mcp_server` in-process tools | **Confirmed.** Signature `(name, version, tools)`, runs in-process, tools via `@tool`. Python handler: only `content` and `is_error` forwarded (no `structuredContent`). | custom-tools |
| Tool names `mcp__server__tool` | **Confirmed**, server = key in `mcp_servers`. | hooks, custom-tools |
| PreToolUse hook deny works for MCP tools | **Confirmed in docs** (matcher `^mcp__` example, `hookSpecificOutput.permissionDecision="deny"`). Docs do not state explicitly that SDK-type (in-process) servers fire hooks; it is implied. Needs the AD-5 test to prove it. | hooks |
| `disallowed_tools` can list built-ins | **Confirmed.** Bare name removes tool from context; scoped rules deny calls; `["*"]` and `mcp__*` globs supported. | permissions |
| `ResultMessage` exposes `total_cost_usd`, `usage`, `model_usage` | **Confirmed.** Caveats below. | python ref |
| `max_budget_usd` | **Confirmed.** Client-side estimate; "can exceed it, leave headroom". | python ref |
| `task_budget` | **Exists as an option but doubtful in this use.** See F3. | python ref; task-budgets page |
| `claude-sonnet-5-5`, `claude-haiku-5-5` valid | **Confirmed.** Pinned snapshot IDs, retirement not before 2027-09-28 / 2027-10-07. Sonnet 5.5 $2/$10 per MTok; Haiku 5.5 from $0.10/$0.50. | models overview |

## 3. Findings

### F1 (High) AD-5: `tools` does not restrict MCP tools
Spine: "Each session sets `tools` to exactly its role tools". Docs: `tools` is the **built-in** availability list; "MCP tools are unaffected"; `tools: []` removes all built-ins. So the role allowlist cannot be enforced by `tools`. Fix wording: `tools=[]` (cleaner than listing every built-in in `disallowed_tools`, which also works), expose only that role's `mcp_servers` entry, and keep the PreToolUse hook as the real gate. Also: SDK MCP tools are deferred by tool search by default, so the model may call `ToolSearch` first; the hook allowlist must permit it or tool search should be disabled, otherwise roles may fail on the first call.

### F2 (High) AD-5: hook failure fails open, and default mode denies unapproved tools
- A PreToolUse callback that raises or returns nothing lets the call proceed to normal permissions. Docs: set `on_failure="block"` on `HookMatcher` (Python SDK >=0.2.177, needs a supporting CLI; older CLI raises `CLIConnectionError`). Add to AD-5 and the minimum SDK version.
- Hook timeout also blocks (good), but hooks may not fire after `max_turns` is hit.
- From Claude Code 2.1.302, default permission mode denies anything needing approval. Allowlisted role tools therefore need `allowed_tools=["mcp__srv__tool", ...]` (or a hook `allow`) in addition to the deny hook. The spine says only that `allowed_tools` "only auto-approves" and never lists it as required. Add `allowed_tools` plus `permission_mode="dontAsk"` for a hard-deny default.
- Matching multiple hooks: deny wins; hooks run in parallel, so the logging hook must not depend on the deny hook's result (log `allowed` inside the single gate hook).

### F3 (High) AD-7/AD-8: `task_budget` likely has no effect through the Agent SDK
Python reference lists `task_budget` (added 0.1.51, sends `output_config.task_budget` with beta `task-budgets-2026-03-13`; min total 20,000). Sonnet 5.5 and Haiku 5.5 are supported at the API. But the task-budgets page states: "Task budgets are not supported on Claude Code or Cowork surfaces", and the Agent SDK drives the Claude Code CLI. Unconfirmed whether the option is honoured or silently ignored. It is also advisory, not a cap, and a too-small value can cause refusal-like early stops. Recommendation: treat `max_budget_usd` + `max_turns` + ledger as the only enforced controls; either drop `task_budget` from the config or add a build-time smoke test that proves it changes behaviour, and record it as "advisory, unverified".

### F4 (Medium) AD-7: `thinking` config shape
Models page: Sonnet 5.5 and Haiku 5.5 use adaptive thinking; manual `{"type":"enabled","budget_tokens":N}` is "not accepted on later models"; `disabled` is unsupported on Sonnet 5.5. The SDK Python reference example nevertheless shows `thinking={"type":"enabled",...}` with `claude-sonnet-5-5` (docs conflict). Pin `thinking={"type":"adaptive"}` plus `effort` (default `high` on Sonnet 5.5, `medium` on Haiku 5.5, so dev and eval differ unless effort is set explicitly; set it in config). Dev (Haiku) vs eval (Sonnet) behaviour differences are therefore larger than the spine implies.

### F5 (Medium) AD-8: cost fields are partial
- `usage` covers the main loop only and excludes subagents/compaction; docs recommend `model_usage` for accounting. Ledger should key on `total_cost_usd` plus `model_usage`, not `usage`. `model_usage` keys are camelCase (`inputTokens`, `costUSD`, ...).
- `total_cost_usd` is cumulative in streaming-input mode (read the last result, do not sum).
- Docs call all of it an estimate, which the spine already labels. Good.
- `max_budget_usd` stops at the estimate and can overshoot; with six parallel sessions the overshoot multiplies. Reserve headroom in the per-session share.

### F6 (Low) AD-7: sampling claim is plausible but unverified
"Agent SDK exposes no temperature/top_p/max_tokens": not contradicted by the options table I read (no such fields). I did not fetch a page stating the models' sampling-parameter rules (that fetch returned nothing). Mark as "no option found in ClaudeAgentOptions as of 0.2.187" rather than a fact about the models.

### F7 (Low) Process
- Replace the "seen" column in Stack with pinned values above and a `uv.lock`; the footnote in the spine says verification was pending.
- Python SDK bundles its own Claude CLI; record the bundled CLI version in `capture.json`/`run.json` alongside the SDK version (reproducibility, AD-7).
- Cost cap: spine defers to "live pricing at build time". Current pricing already known: Sonnet 5.5 $2/$10, Haiku 5.5 from $0.10/$0.50 per MTok; cap can be sized now.
- Docs gap noted: the Python SDK page was truncated past 100k chars on my fetch for `HookMatcher` and `SettingSource` type definitions; the hooks page covered `HookMatcher` usage fully, so no claim depends on that gap.

## 4. Not verified
- Playwright Python and pydantic/FastAPI release notes (only registry versions checked, not behaviour changes).
- axe-core 4.14.1 rule-set changes against WCAG 2.2 criteria used (e.g. 2.4.11 target-size/focus rules).
- Whether in-process SDK MCP tools fire PreToolUse in practice (docs imply yes; AD-5 test must demonstrate).
- Whether `task_budget` is honoured by the CLI (F3).
