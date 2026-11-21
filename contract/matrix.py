"""Criteria Matrix models (AD-7, AD-10). Pure data; loaded by store.config, used by postprocess."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from contract.enums import IssueType, Role, Severity
from contract.models import Criterion


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class CriterionEntry(_Frozen):
    criterion: Criterion
    name: str
    level: Literal["A", "AA"]
    type: IssueType
    roles: list[Role] = Field(min_length=1)
    severity: Severity  # default severity of a failure of this criterion (see postprocess.rank)
    rule_ids: list[str] = Field(default_factory=list)  # native axe rule ids that map here


class CriteriaMatrix(_Frozen):
    schema_version: Literal["1"]
    status: Literal["draft", "frozen"]
    frozen_on: str | None
    criteria: list[CriterionEntry] = Field(min_length=1)

    @model_validator(mode="after")
    def _frozen_needs_a_date(self):
        if (self.status == "frozen") != (self.frozen_on is not None):
            raise ValueError("status 'frozen' requires frozen_on, and 'draft' must not have one")
        return self

    def entry(self, criterion: str) -> CriterionEntry | None:
        return next((c for c in self.criteria if c.criterion == criterion), None)

    def criteria_for_rule(self, rule_id: str) -> list[str]:
        """Criteria a native rule expands to, in matrix order (one rule may yield several)."""
        return [c.criterion for c in self.criteria if rule_id in c.rule_ids]
