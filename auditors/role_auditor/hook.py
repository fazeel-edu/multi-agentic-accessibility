"""PreToolUse allowlist hook (AD-5): every tool call is logged; anything off the list is denied."""

import hashlib
import json
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

from contract.enums import Role
from contract.models import ToolCall

BUILTIN_TOOLS = [
    "Bash",
    "Read",
    "Write",
    "Edit",
    "MultiEdit",
    "NotebookEdit",
    "Glob",
    "Grep",
    "WebFetch",
    "WebSearch",
    "Task",
    "Agent",
    "TodoWrite",
    "Skill",
    "ToolSearch",
    "BashOutput",
    "KillShell",
    "ExitPlanMode",
    "SlashCommand",
]


def args_hash(tool_input: Any) -> str:
    return hashlib.sha256(json.dumps(tool_input, sort_keys=True, default=str).encode()).hexdigest()[
        :16
    ]


def make_allowlist_hook(
    role: Role, allowed: list[str], sink: list[ToolCall]
) -> Callable[[dict[str, Any], str | None, Any], Awaitable[dict[str, Any]]]:
    """Build the hook. A call is allowed only if its exact name is in `allowed`; each call is
    appended to `sink`. Registered with on_failure="block", so a hook that raises blocks the call."""
    allowed_set = frozenset(allowed)

    async def hook(
        hook_input: dict[str, Any], tool_use_id: str | None, context: Any
    ) -> dict[str, Any]:
        name = str(hook_input.get("tool_name", ""))
        ok = name in allowed_set
        sink.append(
            ToolCall(
                role=role,
                tool=name,
                args_hash=args_hash(hook_input.get("tool_input", {})),
                time=datetime.now(UTC).isoformat(timespec="milliseconds"),
                allowed=ok,
            )
        )
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow" if ok else "deny",
                "permissionDecisionReason": "on the role allowlist"
                if ok
                else f"{name} is not on the {role.value} allowlist",
            }
        }

    return hook
