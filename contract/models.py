"""Shared contract models (AD-2). Pure data; no I/O, no project imports.

Agent-set fields live on `Issue` (extra="forbid", so code-set fields are rejected
when parsing agent output). Code-set fields appear only on `KeyedIssue`/`MergedIssue`.
Embedded value types (keys, failure records, usage) do not carry `schema_version`;
every top-level stored or exported model does.
"""

import hashlib
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from contract.element_key import ElementKey
from contract.enums import IssueType, Phase, Role, RoleState, RunState, Scope, Severity, System

SCHEMA_VERSION = "1"

Criterion = Annotated[str, StringConstraints(pattern=r"^\d\.\d{1,2}\.\d{1,2}$")]
NonEmpty = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class ContractModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", use_enum_values=False)
    schema_version: Literal["1"] = SCHEMA_VERSION


class _Embedded(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


# --- Issues -----------------------------------------------------------------


class Issue(ContractModel):
    """What an agent or adapter reports. No code-set fields allowed."""

    element: str | None = None  # CSS selector or XPath; may be absent
    criterion: Criterion | None = None
    rule_id: str | None = None  # axe native rule id
    role: Role
    evidence: NonEmpty
    description: NonEmpty
    suggested_fix: str = ""
    derived_from: list[str] = Field(default_factory=list)  # synthesis only


class AgentOutput(ContractModel):
    """Whole output of one role or synthesis session."""

    issues: list[Issue] = Field(default_factory=list)
    priority_notes: list[str] = Field(default_factory=list)  # synthesis; not Issues


def issue_id(
    element_key: ElementKey, criterion: str | None, role: Role, rule_id: str | None = None
) -> str:
    """Stable id: hash of element_key + criterion + role (+ native rule_id when given, so two
    rules on one element with no criterion stay distinct)."""
    payload = f"{element_key.model_dump_json()}|{criterion or ''}|{role.value}"
    if rule_id:
        payload += f"|{rule_id}"
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def merged_id(element_key: ElementKey, criterion: str) -> str:
    """Stable id of a merged issue: hash of element_key + criterion."""
    return hashlib.sha256(f"{element_key.model_dump_json()}|{criterion}".encode()).hexdigest()[:16]


class KeyedIssue(Issue):
    """An Issue after code resolved its element (stored in issues.jsonl)."""

    element_key: ElementKey
    id: str


class MergedIssue(ContractModel):
    """De-duplicated Issue; every field here except text is set by code."""

    id: str
    element_key: ElementKey
    criterion: Criterion
    roles: list[Role] = Field(min_length=1)  # sorted, excludes inclusive_design echoes
    confidence: int = Field(ge=1, le=6)  # == len(roles) for non-synthesis-only issues
    severity: Severity
    rank: int = Field(ge=1)
    grounded: bool
    evidence: list[NonEmpty] = Field(min_length=1)
    description: NonEmpty
    suggested_fix: str = ""
    derived_from: list[str] = Field(default_factory=list)


# --- Ground truth -----------------------------------------------------------


class GroundTruthItem(ContractModel):
    page_id: str
    element_key: ElementKey
    acceptable_criteria: list[Criterion] = Field(min_length=1)
    affected_user_group: Role
    expected_roles: list[Role] = Field(default_factory=list)
    severity: Severity
    issue_type: IssueType
    scope: Scope = Scope.ELEMENT


class PageGroundTruth(ContractModel):
    page_id: str
    items: list[GroundTruthItem]
    no_issue_criteria: list[Criterion] = Field(default_factory=list)


# --- Run, audit result, report ---------------------------------------------


class FailureRecord(_Embedded):
    stage: str
    kind: str
    message: str
    retryable: bool


class RoleStatus(_Embedded):
    role: Role
    state: RoleState
    failure: FailureRecord | None = None


class Usage(_Embedded):
    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0  # SDK estimate


class ToolCall(_Embedded):
    role: Role
    tool: str
    args_hash: str
    time: str  # ISO 8601 UTC
    allowed: bool


class AuditResult(ContractModel):
    """What every Auditor returns (AD-1)."""

    raw_issues: list[Issue]
    role_status: list[RoleStatus]
    needs_review: list[Issue] = Field(default_factory=list)  # axe "needs review"
    priority_notes: list[str] = Field(default_factory=list)
    usage: Usage = Field(default_factory=Usage)
    seconds: float = 0.0
    tool_calls: list[ToolCall] = Field(default_factory=list)


class Run(ContractModel):
    run_id: str
    system: System
    page_id: str
    phase: Phase
    group_id: str
    state: RunState = RunState.COMPLETE
    model_id: str | None = None  # None for axe
    config_hash: str
    capture_hash: str
    versions: dict[str, str] = Field(default_factory=dict)  # SDK, CLI, tools
    variant: list[Role] = Field(default_factory=list)  # excluded roles (ablation)
    provider_terms_date: str | None = None
    role_status: list[RoleStatus] = Field(default_factory=list)
    usage: Usage = Field(default_factory=Usage)
    seconds: float = 0.0
    started_at: str  # ISO 8601 UTC


class Report(ContractModel):
    run_id: str
    system: System
    page_id: str
    phase: Phase
    group_id: str
    capture_hash: str
    config_hash: str
    postprocess_version: str
    role_status: list[RoleStatus]
    cannot_test_statement: NonEmpty
    priority_notes: list[str] = Field(default_factory=list)
    issues: list[MergedIssue] = Field(default_factory=list)
    # Issues with no criterion after mapping: kept for review, excluded from matching,
    # ranking and Confidence.
    unmapped_issues: list[KeyedIssue] = Field(default_factory=list)
