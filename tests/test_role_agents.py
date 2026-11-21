import asyncio
import json

import pytest

from auditors.role_auditor import prompts
from auditors.role_auditor.hook import BUILTIN_TOOLS, args_hash, make_allowlist_hook
from auditors.role_auditor.orchestrator import ROLES, audit, run_state
from auditors.role_auditor.role_runner import AgentContext, OutputGateError, parse_output, run_agent
from contract.enums import Role, RoleState, RunState
from contract.errors import OrchestrationError
from store.config import load
from store.ledger import Ledger
from store.roles import load_role_specs
from tests.conftest import make_capture
from tests.fakes import FakeRunner, answer, issue, provider_error

LOADED = load()
SPECS = load_role_specs()
CAPTURE = make_capture()
SR, KB, CV, CG, PL, WS, ID = (
    Role.SCREEN_READER,
    Role.KEYBOARD,
    Role.COLOUR_VISUAL,
    Role.COGNITIVE,
    Role.PLAIN_LANGUAGE,
    Role.WCAG_STRUCTURE,
    Role.INCLUSIVE_DESIGN,
)


def make_ctx(tmp_path, runner, cap=100.0, **kw):
    sleeps: list[float] = []

    async def sleep(s):
        sleeps.append(s)

    ctx = AgentContext(
        runner=runner,
        ledger=Ledger(tmp_path / "l.jsonl", cap, 1.0),
        run_id="r-1",
        model=LOADED.config.model_for(__import__("contract.enums", fromlist=["Phase"]).Phase.DEV),
        matrix=LOADED.config.matrix,
        max_turns=5,
        max_budget_usd=1.0,
        sleep=sleep,
        **kw,
    )
    ctx.sleeps = sleeps  # type: ignore[attr-defined]
    return ctx


def run(coro):
    return asyncio.run(coro)


# --- specs and prompts --------------------------------------------------------


def test_all_role_specs_load_and_screen_reader_has_three_to_four_examples():
    assert set(SPECS) == set(Role) - {Role.AXE_CORE}
    assert 3 <= len(SPECS[SR].examples) <= 4
    assert all(s.version == "1" for s in SPECS.values())


def test_system_prompt_lists_only_the_roles_criteria():
    text = prompts.system_prompt(SPECS[CV], LOADED.config.matrix)
    assert "1.4.3 Contrast" in text and "2.1.1 Keyboard" not in text and "Example 1" in text
    assert "WCAG 2.2 criteria" not in prompts.system_prompt(SPECS[ID], LOADED.config.matrix)


def test_user_prompt_holds_only_the_named_inputs():
    cap = make_capture(accessibility_tree="TREE-MARK", computed_styles={"#a": {"color": "red"}})
    sr = prompts.user_prompt(SPECS[SR], cap)
    assert "TREE-MARK" in sr and "computed_styles" not in sr
    assert "## html" in prompts.user_prompt(SPECS[CV], cap) and "color" in prompts.user_prompt(
        SPECS[CV], cap
    )
    assert "TREE-MARK" not in prompts.user_prompt(SPECS[CV], cap)


def test_visible_text_drops_scripts_and_hidden_nodes():
    from tools.element import visible_text

    text = visible_text(CAPTURE.html)
    assert "Click here" in text and "Size guide" not in text and "<script" not in text


# --- hook ----------------------------------------------------------------------


def test_hook_allows_listed_tool_denies_others_and_logs_both():
    sink = []
    hook = make_allowlist_hook(KB, ["mcp__a11y__focus_trace"], sink)
    ok = run(hook({"tool_name": "mcp__a11y__focus_trace", "tool_input": {}}, "1", None))
    no = run(hook({"tool_name": "Bash", "tool_input": {"command": "ls"}}, "2", None))
    assert ok["hookSpecificOutput"]["permissionDecision"] == "allow"
    assert no["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert [(c.tool, c.allowed) for c in sink] == [
        ("mcp__a11y__focus_trace", True),
        ("Bash", False),
    ]
    assert sink[1].args_hash == args_hash({"command": "ls"}) and sink[0].role is KB


def test_empty_allowlist_denies_everything():
    sink = []
    out = run(
        make_allowlist_hook(ID, [], sink)({"tool_name": "mcp__a11y__axe_violations"}, None, None)
    )
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "ToolSearch" in BUILTIN_TOOLS and "Bash" in BUILTIN_TOOLS


# --- output gate -----------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    ["", "no json", "{bad", '{"issues": [{"role": "keyboard"}]}', '{"issues": [], "extra": 1}'],
)
def test_gate_rejects_bad_output(text):
    with pytest.raises(OutputGateError):
        parse_output(text, KB)


def test_gate_accepts_fenced_and_prose_wrapped_json():
    body = answer("keyboard", issue("#size-btn", "2.1.1"))
    assert len(parse_output(f"```json\n{body}\n```", KB).issues) == 1
    assert len(parse_output(f"Here you go: {body} done", KB).issues) == 1


def test_gate_requires_evidence_and_synthesis_derived_from():
    with pytest.raises(OutputGateError):
        parse_output(
            json.dumps({"issues": [{"role": "keyboard", "evidence": "", "description": "x"}]}), KB
        )
    with pytest.raises(OutputGateError, match="derived_from"):
        parse_output(answer("inclusive_design", issue()), ID)
    assert parse_output(answer("inclusive_design", issue(derived_from=["keyboard"])), ID).issues


# --- one role -----------------------------------------------------------------------


def one(tmp_path, runner, role=SR, **kw):
    ctx = make_ctx(tmp_path, runner, **kw)
    return run(run_agent(SPECS[role], prompts.user_prompt(SPECS[role], CAPTURE), CAPTURE, ctx)), ctx


def test_role_ok_records_status_prompt_size_examples_and_cost(tmp_path):
    out, ctx = one(tmp_path, FakeRunner({SR: [answer("screen_reader", issue())]}))
    s = out.status
    assert s.state is RoleState.OK and s.attempts == 1 and s.schema_valid is True
    assert s.example_count == 3 and s.prompt_tokens_est > 100 and s.cost_usd == pytest.approx(0.1)
    assert (
        out.usage.calls == 1
        and out.usage.input_tokens == 10
        and ctx.ledger.spent() == pytest.approx(0.1)
    )
    assert out.issues[0].role is SR


def test_role_field_is_set_by_code_not_the_model(tmp_path):
    out, _ = one(tmp_path, FakeRunner({SR: [answer("keyboard", issue())]}))
    assert out.issues[0].role is SR


def test_output_gate_retries_once_then_succeeds(tmp_path):
    runner = FakeRunner({SR: ["not json", answer("screen_reader", issue())]})
    out, ctx = one(tmp_path, runner)
    assert (
        out.status.state is RoleState.OK
        and out.status.attempts == 2
        and out.status.schema_valid is False
    )
    assert (
        "rejected" in runner.requests[1].user_prompt
        and "rejected" not in runner.requests[0].user_prompt
    )
    assert ctx.ledger.spent() == pytest.approx(0.2)  # both sessions are paid for


def test_output_gate_fails_after_one_retry(tmp_path):
    runner = FakeRunner({SR: ["nope", "still nope", answer("screen_reader")]})
    out, _ = one(tmp_path, runner)
    f = out.status.failure
    assert (
        out.status.state is RoleState.FAILED
        and out.status.attempts == 2
        and len(runner.requests) == 2
    )
    assert (f.stage, f.kind, f.retryable) == ("output_gate", "schema", True) and out.issues == []


def test_retryable_provider_errors_back_off_then_recover(tmp_path):
    runner = FakeRunner({SR: [provider_error(), provider_error(), answer("screen_reader")]})
    out, ctx = one(tmp_path, runner)
    assert out.status.state is RoleState.OK and ctx.sleeps == [1.0, 3.0]  # type: ignore[attr-defined]


def test_provider_errors_are_bounded(tmp_path):
    runner = FakeRunner({SR: [provider_error()] * 5})
    out, ctx = one(tmp_path, runner)
    assert out.status.failure.kind == "rate_limit" and len(runner.requests) == 3
    assert ctx.ledger.spent() == pytest.approx(
        3.0
    )  # failed sessions settle at their full reservation


def test_non_retryable_error_fails_at_once(tmp_path):
    runner = FakeRunner({SR: [provider_error(False, "auth")]})
    out, ctx = one(tmp_path, runner)
    assert out.status.failure.kind == "auth" and len(runner.requests) == 1 and not ctx.sleeps  # type: ignore[attr-defined]


def test_timeout_fails_the_role(tmp_path):
    out, _ = one(tmp_path, FakeRunner({}, delay=1.0), timeout_s=0.05)
    assert out.status.failure.kind == "timeout" and out.status.state is RoleState.FAILED


def test_cost_cap_fails_the_role_without_starting_a_session(tmp_path):
    runner = FakeRunner({})
    out, _ = one(tmp_path, runner, cap=1.5)  # one reservation plus margin does not fit
    assert out.status.failure.kind == "cost_cap" and runner.requests == []


# --- orchestrator --------------------------------------------------------------------


def orch(tmp_path, runner, exclude=frozenset(), **kw):
    ctx = make_ctx(tmp_path, runner, **kw)
    return run(audit(CAPTURE, SPECS, ctx, exclude)), ctx


def test_exactly_one_session_per_role_then_synthesis(tmp_path):
    runner = FakeRunner({})
    result, _ = orch(tmp_path, runner)
    assert sorted(r.value for r in runner.roles_started()) == sorted(r.value for r in [*ROLES, ID])
    assert runner.roles_started()[-1] is ID
    assert [s.role for s in result.role_status] == [*ROLES, ID]
    assert all(s.state is RoleState.OK for s in result.role_status)


def test_roles_run_in_parallel(tmp_path):
    runner = FakeRunner({}, delay=0.05)
    orch(tmp_path, runner)
    assert runner.max_in_flight == 6


def test_one_failed_role_does_not_sink_the_run(tmp_path):
    runner = FakeRunner(
        {KB: [provider_error(False, "auth")], SR: [answer("screen_reader", issue())]}
    )
    result, _ = orch(tmp_path, runner)
    status = {s.role: s for s in result.role_status}
    assert status[KB].state is RoleState.FAILED and status[SR].state is RoleState.OK
    assert [i.role for i in result.raw_issues] == [SR]
    assert "keyboard" in runner.requests[-1].user_prompt.split("## failed_roles")[1]


def test_no_role_sees_another_roles_output(tmp_path):
    runner = FakeRunner({SR: [answer("screen_reader", issue(evidence="SR-ONLY-MARK"))]})
    orch(tmp_path, runner)
    for req in runner.requests:
        if req.role is not ID:
            assert "SR-ONLY-MARK" not in req.user_prompt and "role_outputs" not in req.user_prompt
    assert "SR-ONLY-MARK" in runner.requests[-1].user_prompt


def test_synthesis_has_no_tools_and_returns_issues_and_notes(tmp_path):
    runner = FakeRunner(
        {
            ID: [
                answer(
                    "inclusive_design",
                    issue(derived_from=["screen_reader"]),
                    notes=["fix links first"],
                )
            ]
        }
    )
    result, _ = orch(tmp_path, runner)
    assert result.priority_notes == ["fix links first"]
    synth = [i for i in result.raw_issues if i.role is ID]
    assert synth and synth[0].derived_from == ["screen_reader"]
    from auditors.role_auditor.tool_table import allowed_tool_names

    assert allowed_tool_names(ID) == []


def test_synthesis_failure_keeps_the_six_outputs(tmp_path):
    runner = FakeRunner(
        {SR: [answer("screen_reader", issue())], ID: [provider_error(False, "auth")]}
    )
    result, _ = orch(tmp_path, runner)
    assert result.role_status[-1].role is ID and result.role_status[-1].state is RoleState.FAILED
    assert len(result.raw_issues) == 1 and result.priority_notes == []


def test_all_roles_failing_skips_synthesis(tmp_path):
    runner = FakeRunner({r: [provider_error(False, "auth")] for r in ROLES})
    result, _ = orch(tmp_path, runner)
    assert ID not in runner.roles_started() and result.role_status[-1].failure.kind == "no_input"


def test_exclude_skips_roles_and_records_excluded(tmp_path):
    runner = FakeRunner({})
    result, _ = orch(tmp_path, runner, exclude=frozenset({CG, PL}))
    assert CG not in runner.roles_started() and PL not in runner.roles_started()
    assert {s.role for s in result.role_status if s.state is RoleState.EXCLUDED} == {CG, PL}
    with pytest.raises(OrchestrationError):
        orch(tmp_path, FakeRunner({}), exclude=frozenset({ID}))


def test_cost_cap_stops_the_run_state(tmp_path):
    result, _ = orch(
        tmp_path, FakeRunner({}, delay=0.02), cap=3.5
    )  # room for 2 reservations plus margin
    assert run_state(result.role_status) is RunState.STOPPED_COST_CAP
    assert any(s.state is RoleState.OK for s in result.role_status)


def test_usage_and_seconds_are_summed(tmp_path):
    result, ctx = orch(tmp_path, FakeRunner({}))
    assert result.usage.calls == 7 and result.usage.cost_usd == pytest.approx(0.7)
    assert result.seconds > 0 and ctx.ledger.spent() == pytest.approx(0.7)
