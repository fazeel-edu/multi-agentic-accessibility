"""Which analysis tools each Role may call (least tools, AD-5). Fixed in code, not in a prompt."""

from contract.enums import Role

SERVER_NAME = "a11y"  # every role's in-process MCP server uses this name

ROLE_TOOLS: dict[Role, tuple[str, ...]] = {
    Role.SCREEN_READER: ("axe_violations", "axe_needs_review"),
    Role.KEYBOARD: ("axe_violations", "axe_needs_review", "focus_trace"),
    Role.COLOUR_VISUAL: ("contrast_check", "contrast_failures"),
    Role.COGNITIVE: ("readability",),
    Role.PLAIN_LANGUAGE: ("readability",),
    Role.WCAG_STRUCTURE: ("axe_violations", "axe_needs_review"),
    Role.INCLUSIVE_DESIGN: (),  # Synthesis Agent has no tools
    Role.AXE_CORE: (),  # System A is not an agent
}


def allowed_tool_names(role: Role) -> list[str]:
    """Names as the SDK sees them: `mcp__{server}__{tool}`."""
    return [f"mcp__{SERVER_NAME}__{name}" for name in ROLE_TOOLS[role]]
