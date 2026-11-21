"""Role Spec file model (FR9, FR10). One versioned file per Role; pure data."""

import json
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from contract.enums import Role
from contract.models import AgentOutput, NonEmpty

INPUT_NAMES = (
    "accessibility_tree",
    "html",
    "computed_styles",
    "focus_trace",
    "visible_text",
    "axe_summary",
)


class ExampleKind(StrEnum):
    ISSUE = "issue"  # a clear issue
    CLEAN = "clean"  # correctly no issue
    BORDERLINE = "borderline"


class WorkedExample(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: ExampleKind
    source_page_id: NonEmpty  # must be a reviewed Dev page at Prompt Freeze (AD-12)
    situation: NonEmpty  # what the Role is shown
    output: str  # the JSON the Role should answer with

    @model_validator(mode="after")
    def _output_is_valid_agent_output(self):
        AgentOutput.model_validate_json(self.output)
        return self

    def parsed(self) -> AgentOutput:
        return AgentOutput.model_validate_json(self.output)


class RoleSpecFile(BaseModel):
    """The editable parts of a Role Spec. The other parts (criteria subset, tool allowlist,
    output schema) come from the Criteria Matrix, the tool table and the contract."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["1"] = "1"
    version: NonEmpty
    role: Role
    prompt: NonEmpty
    guidance: NonEmpty
    inputs: list[Literal[*INPUT_NAMES]] = Field(min_length=1)
    examples: list[WorkedExample] = Field(default_factory=list)

    @model_validator(mode="after")
    def _examples_fit_the_role(self):
        for ex in self.examples:
            for issue in ex.parsed().issues:
                if issue.role != self.role:
                    raise ValueError(f"example issue role {issue.role} is not {self.role}")
        return self


def example_json(output: dict) -> str:
    return json.dumps(output, indent=2)
