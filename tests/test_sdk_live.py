"""Story 2.1: live checks of the SDK assumptions. Skipped unless ANTHROPIC_API_KEY is set.

Run with: ANTHROPIC_API_KEY=... uv run pytest tests/test_sdk_live.py -s
Each test makes one small paid session (budget capped at USD 0.25).
"""

import asyncio
import os

import pytest

from auditors.role_auditor.sdk_runner import SdkSessionRunner
from auditors.role_auditor.session import SessionRequest
from contract.enums import Role
from tests.conftest import make_capture

pytestmark = pytest.mark.skipif(not os.environ.get("ANTHROPIC_API_KEY"), reason="ANTHROPIC_API_KEY not set")


def request(role: Role, prompt: str) -> SessionRequest:
    return SessionRequest(
        role=role, system_prompt="Follow the user's instructions exactly.", user_prompt=prompt,
        capture=make_capture(), model_id="claude-haiku-5-5", effort="low", max_turns=4, max_budget_usd=0.25,
    )


def test_allowlisted_tool_is_allowed_and_off_list_tool_is_denied():
    result = asyncio.run(
        SdkSessionRunner().run(
            request(
                Role.COGNITIVE,
                "Call the tool readability with text 'The cat sat.' then try to call the tool "
                "mcp__a11y__axe_violations, then say DONE.",
            )
        )
    )
    calls = {c.tool: c.allowed for c in result.tool_calls}
    assert calls.get("mcp__a11y__readability") is True, calls
    assert calls.get("mcp__a11y__axe_violations", False) is False, calls  # denied or never reachable
    assert result.total_cost_usd > 0


def test_builtin_tools_are_unavailable():
    result = asyncio.run(
        SdkSessionRunner().run(request(Role.COGNITIVE, "Run the shell command `ls` using the Bash tool, then say DONE."))
    )
    assert not any(c.allowed and c.tool == "Bash" for c in result.tool_calls)
