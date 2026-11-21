"""Port between the orchestrator and a model session. The SDK adapter and test fakes implement it."""

from dataclasses import dataclass, field
from typing import Any, Protocol

from contract.capture import Capture
from contract.enums import Role
from contract.models import ToolCall


@dataclass(frozen=True)
class SessionRequest:
    role: Role
    system_prompt: str
    user_prompt: str
    capture: Capture  # tools read from it; the model never gets files
    model_id: str
    effort: str
    max_turns: int
    max_budget_usd: float


@dataclass
class SessionResult:
    text: str  # the model's final answer
    total_cost_usd: float  # final cumulative SDK estimate
    model_usage: dict[str, Any] = field(default_factory=dict)
    tool_calls: list[ToolCall] = field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0


class SessionRunner(Protocol):
    async def run(self, request: SessionRequest) -> SessionResult:
        """Run one isolated session. Raises ProviderError on provider or SDK failure."""
        ...
