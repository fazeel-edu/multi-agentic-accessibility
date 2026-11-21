"""One Role session with output gate, one retry, bounded provider retries and ledger accounting."""

import asyncio
import json
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

from pydantic import ValidationError

from auditors.role_auditor import prompts
from auditors.role_auditor.session import SessionRequest, SessionRunner
from contract.capture import Capture
from contract.enums import Role, RoleState
from contract.errors import CostCapReached, ProviderError, RunStopped
from contract.matrix import CriteriaMatrix
from contract.models import AgentOutput, FailureRecord, Issue, RoleStatus, ToolCall, Usage
from contract.role_spec import RoleSpecFile
from store.config import ModelSettings
from store.ledger import Ledger

PROVIDER_RETRIES = 2
BACKOFF_SECONDS = (1.0, 3.0)
SESSION_TIMEOUT_S = 300.0


@dataclass
class AgentContext:
    runner: SessionRunner
    ledger: Ledger
    run_id: str
    model: ModelSettings
    matrix: CriteriaMatrix
    max_turns: int
    max_budget_usd: float
    allow_resume: bool = False
    timeout_s: float = SESSION_TIMEOUT_S
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep


@dataclass
class RoleOutcome:
    status: RoleStatus | None = None
    issues: list[Issue] = field(default_factory=list)
    priority_notes: list[str] = field(default_factory=list)
    tool_calls: list[ToolCall] = field(default_factory=list)
    usage: Usage = field(default_factory=Usage)


class OutputGateError(ValueError):
    """The model's answer is not a valid AgentOutput."""


def parse_output(text: str, role: Role) -> AgentOutput:
    """Extract the JSON object from the answer and validate it (the output gate)."""
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        raise OutputGateError("no JSON object in the answer")
    try:
        out = AgentOutput.model_validate(json.loads(text[start : end + 1]))
    except (json.JSONDecodeError, ValidationError) as exc:
        raise OutputGateError(str(exc)[:500]) from exc
    if role is Role.INCLUSIVE_DESIGN and any(not i.derived_from for i in out.issues):
        raise OutputGateError("every synthesis issue needs derived_from")
    return out


def _failure(stage: str, kind: str, message: str, retryable: bool) -> FailureRecord:
    return FailureRecord(stage=stage, kind=kind, message=message[:500], retryable=retryable)


async def run_agent(
    spec: RoleSpecFile, user_prompt_text: str, capture: Capture, ctx: AgentContext
) -> RoleOutcome:
    """Run one Role (or the Synthesis Agent). Never raises for model or provider trouble: the
    outcome carries `failed` with a FailureRecord and the Run continues."""
    role = spec.role
    system = prompts.system_prompt(spec, ctx.matrix)
    started = time.monotonic()
    st: dict = {  # RoleStatus is frozen: collect the fields, build it once at the end
        "role": role,
        "state": RoleState.FAILED,
        "failure": None,
        "attempts": 0,
        "schema_valid": None,
        "prompt_tokens_est": prompts.estimate_tokens(system, user_prompt_text),
        "example_count": len(spec.examples),
    }
    out = RoleOutcome()
    prompt, last_error = user_prompt_text, ""
    for attempt in (1, 2):  # the output gate allows one retry
        try:
            result = await _session(role, system, prompt, capture, ctx, out)
        except (CostCapReached, RunStopped) as exc:
            st["failure"] = _failure("session", "cost_cap", str(exc), False)
            break
        except ProviderError as exc:
            st["failure"] = _failure("session", exc.kind, str(exc), exc.retryable)
            break
        st["attempts"] = attempt
        try:
            parsed = parse_output(result.text, role)
        except OutputGateError as exc:
            last_error = str(exc)
            if attempt == 1:
                st["schema_valid"] = False
            st["failure"] = _failure("output_gate", "schema", last_error, True)
            prompt = (
                f"{user_prompt_text}\n\nYour previous answer was rejected: {last_error}\n"
                "Answer again with only the JSON object."
            )
            continue
        if attempt == 1:
            st["schema_valid"] = True
        out.issues = [
            i.model_copy(update={"role": role}) for i in parsed.issues
        ]  # code sets the role
        out.priority_notes = parsed.priority_notes if role is Role.INCLUSIVE_DESIGN else []
        st["state"], st["failure"] = RoleState.OK, None
        break
    out.status = RoleStatus(
        **st, seconds=round(time.monotonic() - started, 3), cost_usd=out.usage.cost_usd
    )
    return out


async def _session(role, system, prompt, capture, ctx: AgentContext, out: RoleOutcome):
    """One session: reserve budget, run with bounded provider retries and a timeout, settle."""
    req = SessionRequest(
        role=role,
        system_prompt=system,
        user_prompt=prompt,
        capture=capture,
        model_id=ctx.model.model_id,
        effort=ctx.model.effort,
        max_turns=ctx.max_turns,
        max_budget_usd=ctx.max_budget_usd,
    )
    result = None
    for retry in range(PROVIDER_RETRIES + 1):
        # every attempt is a session: reserve first, settle after (unknown cost on failure: the
        # whole reservation, so spend is never under-counted)
        reservation = ctx.ledger.reserve(
            ctx.run_id, role.value, ctx.max_budget_usd, allow_resume=ctx.allow_resume
        )
        cost, usage = ctx.max_budget_usd, {}
        try:
            result = await asyncio.wait_for(ctx.runner.run(req), ctx.timeout_s)
            cost, usage = result.total_cost_usd, result.model_usage
            break
        except TimeoutError as exc:
            raise ProviderError("timeout", f"session exceeded {ctx.timeout_s:.0f}s", False) from exc
        except ProviderError as exc:
            if not exc.retryable or retry == PROVIDER_RETRIES:
                raise
        finally:
            ctx.ledger.settle(reservation, cost, usage)
        await ctx.sleep(BACKOFF_SECONDS[min(retry, len(BACKOFF_SECONDS) - 1)])
    out.tool_calls += result.tool_calls
    out.usage = Usage(
        calls=out.usage.calls + 1,
        input_tokens=out.usage.input_tokens + result.input_tokens,
        output_tokens=out.usage.output_tokens + result.output_tokens,
        cost_usd=out.usage.cost_usd + cost,
    )
    return result
