"""A scripted SessionRunner: no model, no network."""

import asyncio
import json

from auditors.role_auditor.session import SessionRequest, SessionResult
from contract.enums import Role
from contract.errors import ProviderError


def answer(role: str, *issues: dict, notes: list[str] | None = None) -> str:
    return json.dumps(
        {"issues": [{"role": role, **i} for i in issues], "priority_notes": notes or []}
    )


def issue(element="#hero", criterion="1.1.1", **kw):
    return {
        "element": element,
        "criterion": criterion,
        "evidence": "seen",
        "description": "bad",
        **kw,
    }


class FakeRunner:
    """`script[role]` is a list consumed one per session: a str answer, an Exception, or a callable."""

    def __init__(self, script: dict[Role, list], cost: float = 0.1, delay: float = 0.0):
        self.script = {r: list(v) for r, v in script.items()}
        self.cost, self.delay = cost, delay
        self.requests: list[SessionRequest] = []
        self.in_flight = self.max_in_flight = 0

    async def run(self, request: SessionRequest) -> SessionResult:
        self.requests.append(request)
        self.in_flight += 1
        self.max_in_flight = max(self.max_in_flight, self.in_flight)
        try:
            if self.delay:
                await asyncio.sleep(self.delay)
            queue = self.script.get(request.role, [])
            item = queue.pop(0) if queue else answer(request.role.value)
            if isinstance(item, Exception):
                raise item
            if callable(item):
                item = item(request)
            return SessionResult(
                text=item,
                total_cost_usd=self.cost,
                model_usage={"m": {"cost": self.cost}},
                input_tokens=10,
                output_tokens=5,
            )
        finally:
            self.in_flight -= 1

    def roles_started(self) -> list[Role]:
        return [r.role for r in self.requests]


def provider_error(retryable=True, kind="rate_limit", cost=None, calls=None):
    return ProviderError(kind, "boom", retryable, cost_usd=cost, tool_calls=calls)
