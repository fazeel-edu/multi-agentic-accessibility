"""In-process SDK MCP servers over a loaded Capture, one per Role, holding only that Role's tools."""

from typing import Any

from claude_agent_sdk import McpSdkServerConfig, SdkMcpTool, create_sdk_mcp_server, tool

from auditors.role_auditor.tool_table import ROLE_TOOLS, SERVER_NAME
from contract.capture import Capture
from contract.enums import Role
from tools.registry import TOOLS, ToolSpec


def _wrap(spec: ToolSpec, capture: Capture) -> SdkMcpTool[Any]:
    @tool(spec.name, spec.description, spec.input_schema)
    async def handler(args: dict[str, Any]) -> dict[str, Any]:
        try:
            text = spec.run(capture, args or {})
        except (KeyError, TypeError, ValueError) as exc:  # bad arguments from the model
            return {"content": [{"type": "text", "text": f"error: {exc}"}], "is_error": True}
        return {"content": [{"type": "text", "text": text}]}

    return handler


def role_tools(role: Role, capture: Capture) -> list[SdkMcpTool[Any]]:
    """The SDK tools of one Role, in table order."""
    return [_wrap(TOOLS[name], capture) for name in ROLE_TOOLS[role]]


def build_role_server(role: Role, capture: Capture) -> McpSdkServerConfig | None:
    """The server a Role's session mounts, or None when the Role has no tools."""
    tools = role_tools(role, capture)
    if not tools:
        return None
    return create_sdk_mcp_server(name=SERVER_NAME, version="1.0.0", tools=tools)
