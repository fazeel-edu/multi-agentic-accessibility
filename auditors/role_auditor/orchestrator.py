"""Plain-Python orchestrator (not an agent): six Role sessions in parallel, then Synthesis (AD-4)."""

import asyncio
import time

from auditors.role_auditor import prompts
from auditors.role_auditor.role_runner import AgentContext, RoleOutcome, run_agent
from contract.capture import Capture
from contract.enums import Role, RoleState, RunState
from contract.errors import OrchestrationError
from contract.models import AuditResult, FailureRecord, RoleStatus, Usage
from contract.role_spec import RoleSpecFile

ROLES: tuple[Role, ...] = (
    Role.SCREEN_READER,
    Role.KEYBOARD,
    Role.COLOUR_VISUAL,
    Role.COGNITIVE,
    Role.PLAIN_LANGUAGE,
    Role.WCAG_STRUCTURE,
)  # the fixed table: no routing, no model choice


def run_state(statuses: list[RoleStatus]) -> RunState:
    if any(s.failure and s.failure.kind == "cost_cap" for s in statuses):
        return RunState.STOPPED_COST_CAP
    return RunState.COMPLETE


async def audit(
    capture: Capture,
    specs: dict[Role, RoleSpecFile],
    ctx: AgentContext,
    exclude: frozenset[Role] = frozenset(),
) -> AuditResult:
    """Run the fixed table, then the Synthesis Agent. `exclude` is for ablation only."""
    if not exclude <= set(ROLES):
        raise OrchestrationError(
            f"exclude may only hold the six roles, got {sorted(r.value for r in exclude)}"
        )
    started = time.monotonic()
    active = [r for r in ROLES if r not in exclude]
    outcomes = await asyncio.gather(
        *(run_agent(specs[r], prompts.user_prompt(specs[r], capture), capture, ctx) for r in active)
    )  # no role receives another role's output
    by_role: dict[Role, RoleOutcome] = dict(zip(active, outcomes, strict=True))
    if list(by_role) != active:
        raise OrchestrationError("a role was skipped, added or repeated")

    ok = {r: o.issues for r, o in by_role.items() if o.status.state is RoleState.OK}
    failed = [r for r, o in by_role.items() if o.status.state is RoleState.FAILED]
    synth_spec = specs[Role.INCLUSIVE_DESIGN]
    if ok:
        synth = await run_agent(
            synth_spec, prompts.synthesis_user_prompt(synth_spec, capture, ok, failed), capture, ctx
        )
    else:  # nothing to synthesise from
        status = RoleStatus(
            role=Role.INCLUSIVE_DESIGN,
            state=RoleState.FAILED,
            failure=FailureRecord(
                stage="synthesis", kind="no_input", message="all six roles failed", retryable=False
            ),
        )
        synth = RoleOutcome(status=status)

    statuses = [
        by_role[r].status if r in by_role else RoleStatus(role=r, state=RoleState.EXCLUDED)
        for r in ROLES
    ] + [synth.status]
    every = [*by_role.values(), synth]
    usage = Usage(
        calls=sum(o.usage.calls for o in every),
        input_tokens=sum(o.usage.input_tokens for o in every),
        output_tokens=sum(o.usage.output_tokens for o in every),
        cost_usd=sum(o.usage.cost_usd for o in every),
    )
    return AuditResult(
        raw_issues=[i for o in every for i in o.issues],
        role_status=statuses,
        priority_notes=synth.priority_notes,
        usage=usage,
        seconds=round(time.monotonic() - started, 3),
        tool_calls=[c for o in every for c in o.tool_calls],
    )
