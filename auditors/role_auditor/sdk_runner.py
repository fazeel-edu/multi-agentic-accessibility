"""Claude Agent SDK adapter for the session port. Needs ANTHROPIC_API_KEY; only `auditors` reads it.

Not exercised without a key: Story 2.1's live tests prove the hook and isolation settings.
"""

import os
import tempfile
from importlib.metadata import version
from pathlib import Path

from auditors.role_auditor.hook import BUILTIN_TOOLS, make_allowlist_hook
from auditors.role_auditor.sdk_tools import build_role_server
from auditors.role_auditor.session import SessionRequest, SessionResult
from auditors.role_auditor.tool_table import SERVER_NAME, allowed_tool_names
from contract.errors import MissingApiKeyError, ProviderError
from contract.models import ToolCall


def api_key() -> str:
    """The key for the session subprocess: process environment first, then the project's
    git-ignored `.env.systemc`. It is passed only to the subprocess, never put in os.environ."""
    from store.secrets import SECRETS_FILE, read_api_key

    key = os.environ.get("ANTHROPIC_API_KEY") or read_api_key()
    if not key:
        raise MissingApiKeyError(
            f"ANTHROPIC_API_KEY not found: put it in {SECRETS_FILE.name} (see .env.systemc.example); never commit it"
        )
    return key


def require_api_key() -> None:
    api_key()


def versions() -> dict[str, str]:
    import claude_agent_sdk

    from store.versions import bundled_cli_version

    return {
        "claude-agent-sdk": version("claude-agent-sdk"),
        "claude-code-cli": bundled_cli_version(Path(claude_agent_sdk.__file__).parent),
    }


class SdkSessionRunner:
    def __init__(self, key: str | None = None) -> None:
        self._key = key

    """One isolated SDK session per call: no settings sources, no built-ins, empty temp cwd."""

    async def run(self, request: SessionRequest) -> SessionResult:
        from claude_agent_sdk import (
            AssistantMessage,
            ClaudeAgentOptions,
            ClaudeSDKError,  # type: ignore[attr-defined]
            HookMatcher,
            ResultMessage,
            TextBlock,
            query,
        )

        key = self._key or api_key()
        calls: list[ToolCall] = []
        server = build_role_server(request.role, request.capture)
        allowed = allowed_tool_names(request.role)
        hook = make_allowlist_hook(request.role, allowed, calls)
        with tempfile.TemporaryDirectory(prefix="systemc-") as cwd:
            options = ClaudeAgentOptions(
                env={"ANTHROPIC_API_KEY": key},
                system_prompt=request.system_prompt,
                tools=[],
                allowed_tools=allowed,
                disallowed_tools=BUILTIN_TOOLS,
                setting_sources=[],
                mcp_servers={SERVER_NAME: server} if server else {},
                strict_mcp_config=True,
                cwd=cwd,
                model=request.model_id,
                effort=request.effort,  # type: ignore[arg-type]
                thinking={"type": "adaptive"},
                max_turns=request.max_turns,
                max_budget_usd=request.max_budget_usd,
                hooks={"PreToolUse": [HookMatcher(matcher=None, hooks=[hook], on_failure="block")]},
            )
            text, final = [], None
            try:
                async for message in query(prompt=request.user_prompt, options=options):
                    if isinstance(message, AssistantMessage):
                        text += [b.text for b in message.content if isinstance(b, TextBlock)]
                    elif isinstance(message, ResultMessage):
                        final = message
            except ClaudeSDKError as exc:
                raise ProviderError("sdk_error", str(exc)[:300], True) from exc
        if final is None:
            raise ProviderError("no_result", "the session ended without a result message", True)
        if final.is_error:
            raise ProviderError(
                final.subtype,
                "; ".join(final.errors or [final.subtype])[:300],
                final.subtype != "error_max_budget_usd",
            )
        usage = final.usage or {}
        return SessionResult(
            text=final.result or "\n".join(text),
            total_cost_usd=float(final.total_cost_usd or 0.0),
            model_usage=dict(final.model_usage or {}),
            tool_calls=calls,
            input_tokens=int(usage.get("input_tokens", 0)),
            output_tokens=int(usage.get("output_tokens", 0)),
        )
