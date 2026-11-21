"""Closed enums shared by every package (AD-2)."""

from enum import IntEnum, StrEnum


class Role(StrEnum):
    SCREEN_READER = "screen_reader"
    KEYBOARD = "keyboard"
    COLOUR_VISUAL = "colour_visual"
    COGNITIVE = "cognitive"
    PLAIN_LANGUAGE = "plain_language"
    WCAG_STRUCTURE = "wcag_structure"
    INCLUSIVE_DESIGN = "inclusive_design"  # Synthesis Agent
    AXE_CORE = "axe_core"  # System A


class Severity(IntEnum):
    """Closed ordinal scale; higher is worse. Set by code, never by an agent."""

    MINOR = 1
    MODERATE = 2
    SERIOUS = 3
    CRITICAL = 4


class IssueType(StrEnum):
    """Criterion type: rule-checkable, judgement, mixed."""

    R = "R"
    J = "J"
    M = "M"


class Scope(StrEnum):
    ELEMENT = "element"
    PAGE = "page"


class Phase(StrEnum):
    DEV = "dev"
    EVAL = "eval"


class System(StrEnum):
    AXE = "axe"
    ROLE_MULTI_AGENT = "role_multi_agent"


class RoleState(StrEnum):
    OK = "ok"
    FAILED = "failed"
    EXCLUDED = "excluded"  # ablation variant only


class RunState(StrEnum):
    COMPLETE = "complete"
    STOPPED_COST_CAP = "stopped_cost_cap"
    FAILED = "failed"
