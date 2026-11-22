"""Epic 2 code-review patches."""

import asyncio
import json

import pytest

from auditors.role_auditor import prompts, sdk_runner
from auditors.role_auditor.orchestrator import audit, run_state
from auditors.role_auditor.role_runner import parse_output
from auditors.role_auditor.session import SessionRequest
from cli import main as cli
from contract.enums import Role, RoleState, RunState
from contract.errors import LedgerError, ProviderError
from contract.models import RoleStatus, ToolCall
from store import captures, runs
from tests.conftest import make_capture
from tests.fakes import FakeRunner, answer, issue, provider_error
from tests.test_role_agents import CAPTURE, ROLES, SPECS, SR, make_ctx, one


def run(coro):
    return asyncio.run(coro)


# --- role runner -----------------------------------------------------------------------------


def test_unexpected_error_in_one_role_does_not_sink_the_run(tmp_path):
    ctx = make_ctx(tmp_path, FakeRunner({}))
    real = ctx.ledger.reserve

    def reserve(run_id, session, *a, **k):
        if session == "keyboard":
            raise LedgerError("disk full")
        return real(run_id, session, *a, **k)

    ctx.ledger.reserve = reserve
    result = run(audit(CAPTURE, SPECS, ctx))
    status = {s.role: s for s in result.role_status}
    assert status[Role.KEYBOARD].failure.kind == "internal"
    assert status[Role.SCREEN_READER].state is RoleState.OK


def test_every_attempt_is_counted_in_attempts_usage_and_cost(tmp_path):
    runner = FakeRunner({SR: [provider_error(), provider_error(cost=0.4), answer("screen_reader")]})
    out, ctx = one(tmp_path, runner)
    assert out.status.attempts == 3 and out.usage.calls == 3
    assert out.status.cost_usd == pytest.approx(out.usage.cost_usd)
    assert out.status.cost_usd == pytest.approx(1.0 + 0.4 + 0.1)
    assert ctx.ledger.spent() == pytest.approx(1.5)


def test_failed_session_settles_at_the_reported_cost(tmp_path):
    runner = FakeRunner({SR: [provider_error(False, "error_max_turns", cost=0.3)]})
    out, ctx = one(tmp_path, runner)
    assert out.status.failure.kind == "error_max_turns"
    assert ctx.ledger.spent() == pytest.approx(0.3)


def test_tool_calls_of_failed_sessions_are_kept(tmp_path):
    call = ToolCall(
        role=SR, tool="Bash", args_hash="x", time="2026-11-22T00:00:00+00:00", allowed=False
    )
    out, _ = one(tmp_path, FakeRunner({SR: [provider_error(False, "x", calls=[call])]}))
    assert out.tool_calls == [call]


def test_timeouts_are_retried_with_backoff(tmp_path):
    runner = FakeRunner({}, delay=1.0)
    out, ctx = one(tmp_path, runner, timeout_s=0.02)
    assert out.status.failure.kind == "timeout"
    assert len(runner.requests) == 3 and len(ctx.sleeps) == 2


def test_parse_output_survives_stray_braces():
    body = answer("keyboard", issue("#size-btn", "2.1.1"))
    text = f"I looked at {{the page}} and found:\n{body}\nThat is {{all}}."
    assert len(parse_output(text, Role.KEYBOARD).issues) == 1


# --- run state and CLI -------------------------------------------------------------------------


def test_run_with_every_role_failed_is_a_failed_run(tmp_path):
    fails = {r: [provider_error(False, "auth")] for r in ROLES}
    result = run(audit(CAPTURE, SPECS, make_ctx(tmp_path, FakeRunner(fails))))
    assert run_state(result.role_status) is RunState.FAILED


def test_excluded_roles_do_not_make_a_run_failed():
    statuses = [
        RoleStatus(role=Role.KEYBOARD, state=RoleState.EXCLUDED),
        RoleStatus(role=Role.SCREEN_READER, state=RoleState.OK),
    ]
    assert run_state(statuses) is RunState.COMPLETE


@pytest.fixture
def env(tmp_path, monkeypatch, fixture_capture):
    from functools import partial

    from store import paths, terms

    monkeypatch.setattr(paths, "RESULTS_DIR", tmp_path)
    monkeypatch.setattr(
        captures, "capture_hashes", lambda p: [fixture_capture.manifest.capture_hash]
    )
    monkeypatch.setattr(captures, "read_capture", lambda p, h: fixture_capture)
    monkeypatch.setattr(runs, "write_run", partial(runs.write_run, root=tmp_path))
    monkeypatch.setattr(runs, "write_report", partial(runs.write_report, root=tmp_path))
    monkeypatch.setattr(terms, "require_provider_terms", lambda: "2026-11-20")
    return tmp_path


def test_all_failed_audit_exits_non_zero(env, monkeypatch, capsys):
    runner = FakeRunner({r: [provider_error(False, "auth")] for r in ROLES})
    monkeypatch.setattr(cli, "make_runner", lambda: runner)
    assert cli.main(["audit", "fixture-01"]) == 1
    assert "failed roles" in capsys.readouterr().err


def test_run_versions_include_the_capture_tool_versions(env, monkeypatch, fixture_capture):
    monkeypatch.setattr(cli, "make_runner", lambda: FakeRunner({}))
    assert cli.main(["audit", "fixture-01"]) == 0
    run_dir = next((env / "role_multi_agent" / "fixture-01").iterdir())
    versions = json.loads((run_dir / "run.json").read_text())["versions"]
    assert set(fixture_capture.manifest.versions) <= set(versions)
    assert "claude-agent-sdk" in versions


def test_estimate_above_the_cap_refuses_before_any_session(env, monkeypatch, capsys):
    from store import config

    real = config.load

    def small_cap(*a, **k):
        loaded = real(*a, **k)
        settings = loaded.config.settings.model_copy(update={"cost_cap_usd": 5.0})
        cfg = loaded.config.model_copy(update={"settings": settings})
        return loaded.model_copy(update={"config": cfg})

    monkeypatch.setattr(config, "load", small_cap)
    runner = FakeRunner({})
    monkeypatch.setattr(cli, "make_runner", lambda: runner)
    assert cli.main(["audit", "fixture-01"]) == 1
    assert "does not fit" in capsys.readouterr().err and runner.requests == []


def test_excluding_roles_lowers_the_printed_session_count(env, monkeypatch, capsys):
    monkeypatch.setattr(cli, "make_runner", lambda: FakeRunner({}))
    cli.main(["audit", "fixture-01", "--exclude", "cognitive", "--exclude", "keyboard"])
    assert "5 sessions" in capsys.readouterr().out


def test_bad_exclude_value_is_a_usage_error(env):
    with pytest.raises(SystemExit) as exc:
        cli.main(["audit", "fixture-01", "--exclude", "nope"])
    assert exc.value.code == 2


def test_a_cost_cap_stop_blocks_the_next_audit_until_resume(env, monkeypatch, capsys):
    from contract.errors import CostCapReached
    from store.ledger import Ledger

    ledger = Ledger.for_phase("dev", 50.0, 1.0)
    for i in range(49):  # hold 49 of 50: the next reservation hits the cap and records a stop
        ledger.reserve("old", f"s{i}")
    with pytest.raises(CostCapReached):
        ledger.reserve("old", "over")
    assert ledger.is_stopped()
    runner = FakeRunner({})
    monkeypatch.setattr(cli, "make_runner", lambda: runner)
    assert cli.main(["audit", "fixture-01"]) == 1
    assert "--resume" in capsys.readouterr().err and runner.requests == []


# --- SDK adapter, with the SDK stubbed ------------------------------------------------------------


def _fake_sdk(monkeypatch, messages, raises=None):
    import claude_agent_sdk as sdk

    seen = {}

    async def query(prompt, options):
        seen["options"], seen["prompt"] = options, prompt
        for m in messages:
            yield m
        if raises:
            raise raises

    monkeypatch.setattr(sdk, "query", query)
    return seen


def _result(**kw):
    import claude_agent_sdk as sdk

    base = {
        "subtype": "success", "duration_ms": 1, "duration_api_ms": 1, "is_error": False, "num_turns": 1,
        "session_id": "s", "stop_reason": None, "result": "{}", "total_cost_usd": 0.2,
        "usage": {"input_tokens": 7, "output_tokens": 3}, "model_usage": {"m": {}},
    }  # fmt: skip
    return sdk.ResultMessage(**{**base, **kw})


def _request(role=Role.KEYBOARD):
    return SessionRequest(
        role=role, system_prompt="sys", user_prompt="u", capture=make_capture(),
        model_id="claude-haiku-5-5", effort="low", max_turns=3, max_budget_usd=0.5,
    )  # fmt: skip


def test_sdk_runner_builds_isolated_options_and_maps_the_result(monkeypatch):
    seen = _fake_sdk(monkeypatch, [_result(result='{"issues": []}')])
    res = run(sdk_runner.SdkSessionRunner(key="k").run(_request()))
    o = seen["options"]
    assert o.setting_sources == [] and o.tools == [] and o.strict_mcp_config is True
    assert o.disallowed_tools == sdk_runner.BUILTIN_TOOLS
    assert o.env == {"ANTHROPIC_API_KEY": "k"}
    assert o.allowed_tools == [
        "mcp__a11y__axe_violations", "mcp__a11y__axe_needs_review", "mcp__a11y__focus_trace",
    ]  # fmt: skip
    matcher = o.hooks["PreToolUse"][0]
    assert matcher.on_failure == "block" and len(matcher.hooks) == 1
    assert (res.text, res.total_cost_usd) == ('{"issues": []}', 0.2)
    assert (res.input_tokens, res.output_tokens) == (7, 3)


def test_sdk_runner_synthesis_gets_no_server_and_no_tools(monkeypatch):
    seen = _fake_sdk(monkeypatch, [_result()])
    run(sdk_runner.SdkSessionRunner(key="k").run(_request(Role.INCLUSIVE_DESIGN)))
    assert seen["options"].mcp_servers == {} and seen["options"].allowed_tools == []


@pytest.mark.parametrize(
    ("subtype", "retryable"),
    [("error_during_execution", True), ("error_max_turns", False), ("error_max_budget_usd", False)],
)
def test_sdk_runner_error_results_map_to_provider_errors(monkeypatch, subtype, retryable):
    _fake_sdk(
        monkeypatch, [_result(subtype=subtype, is_error=True, errors=["x"], total_cost_usd=0.7)]
    )
    with pytest.raises(ProviderError) as exc:
        run(sdk_runner.SdkSessionRunner(key="k").run(_request()))
    assert exc.value.retryable is retryable and exc.value.kind == subtype
    assert exc.value.cost_usd == 0.7


def test_sdk_runner_no_result_and_sdk_errors_are_retryable(monkeypatch):
    from claude_agent_sdk import ClaudeSDKError

    _fake_sdk(monkeypatch, [])
    with pytest.raises(ProviderError) as exc:
        run(sdk_runner.SdkSessionRunner(key="k").run(_request()))
    assert exc.value.kind == "no_result" and exc.value.retryable
    _fake_sdk(monkeypatch, [], raises=ClaudeSDKError("boom"))
    with pytest.raises(ProviderError) as exc:
        run(sdk_runner.SdkSessionRunner(key="k").run(_request()))
    assert exc.value.kind == "sdk_error" and exc.value.retryable


def test_sdk_runner_falls_back_to_assistant_text(monkeypatch):
    from claude_agent_sdk import AssistantMessage, TextBlock

    msg = AssistantMessage(content=[TextBlock(text="hello")], model="m")
    _fake_sdk(monkeypatch, [msg, _result(result=None)])
    assert run(sdk_runner.SdkSessionRunner(key="k").run(_request())).text == "hello"


# --- tools and small fixes ---------------------------------------------------------------------------


def test_visible_text_keeps_text_after_removed_nodes():
    from tools.element import visible_text

    html = (
        "<html><head><title>TITLE</title></head><body><p>one<script>x()</script> two</p>"
        "<span hidden>secret</span> three</body></html>"
    )
    text = visible_text(html)
    assert "two" in text and "three" in text
    assert "secret" not in text and "TITLE" not in text


def test_transparent_colours_are_refused():
    from tools import contrast

    with pytest.raises(ValueError, match="alpha"):
        contrast.parse_color("rgba(0, 0, 0, 0.5)")
    assert contrast.parse_color("rgba(10, 20, 30, 1)") == (10, 20, 30)
    with pytest.raises(ValueError):
        contrast.parse_color("rgb(1, 2, 3")


def test_contrast_selector_with_many_or_no_matches(fixture_capture):
    from tools import contrast
    from tools.registry import TOOLS

    assert contrast.failing_rows(fixture_capture, "p.fine-print")[0]["ratio"] == 2.78
    with pytest.raises(ValueError, match="matches no element"):
        contrast.failing_rows(fixture_capture, "#nope")
    out = json.loads(TOOLS["contrast_failures"].run(fixture_capture, {"selector": "#nope"}))
    assert "error" in out


def test_axe_reader_flattens_nested_targets():
    from tools import axe_reader

    assert axe_reader._selector([["iframe", "#x"]]) == "iframe"
    assert axe_reader._selector(None) is None and axe_reader._selector([]) is None


def test_secrets_accept_export_and_inline_comments(tmp_path):
    from store import secrets

    f = tmp_path / "e"
    f.write_text("export ANTHROPIC_API_KEY=abc123 # my key\n")
    assert secrets.read_api_key(f) == "abc123"
    f.write_text('ANTHROPIC_API_KEY="a b" # c\n')
    assert secrets.read_api_key(f) == "a b"


def test_matrix_script_refuses_a_frozen_matrix(tmp_path, monkeypatch):
    import importlib.util
    import pathlib

    path = pathlib.Path(__file__).resolve().parent.parent / "scripts" / "build_axe_rule_map.py"
    spec = importlib.util.spec_from_file_location("build_axe_rule_map", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    frozen = tmp_path / "m.json"
    frozen.write_text(json.dumps({"status": "frozen", "criteria": []}))
    monkeypatch.setattr(module, "MATRIX", frozen)
    with pytest.raises(SystemExit, match="frozen"):
        module.main()


def test_synthesis_prompt_has_one_instruction_and_no_six_role_claim():
    from store.config import load

    spec = SPECS[Role.INCLUSIVE_DESIGN]
    text = prompts.synthesis_user_prompt(spec, CAPTURE, {Role.KEYBOARD: []}, [Role.COGNITIVE])
    assert "Audit this page now" not in text and text.count("JSON object only") == 1
    assert "six" not in prompts.system_prompt(spec, load().config.matrix)
