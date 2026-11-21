"""Step 1: resolve element keys and assign criteria. The only place a criterion is assigned (AD-10)."""

from dataclasses import dataclass

from contract.capture import Capture
from contract.element_key import ElementKey
from contract.matrix import CriteriaMatrix
from contract.models import Issue, KeyedIssue, issue_id
from tools.element import element_key


@dataclass(frozen=True)
class MappedIssue:
    """One reported issue bound to one criterion and one resolved element."""

    issue: Issue
    element_key: ElementKey
    criterion: str


def criteria_for(issue: Issue, matrix: CriteriaMatrix) -> list[str]:
    """Criteria an issue maps to, deterministically.

    A criterion the reporter gave counts only when the matrix lists it. A native rule_id
    expands through the matrix (one rule may yield several criteria). Anything else maps to none.
    """
    if issue.criterion is not None:
        return [issue.criterion] if matrix.entry(issue.criterion) else []
    if issue.rule_id is not None:
        return matrix.criteria_for_rule(issue.rule_id)
    return []


def map_issues(
    raw_issues: list[Issue], capture: Capture, matrix: CriteriaMatrix
) -> tuple[list[MappedIssue], list[KeyedIssue]]:
    """Return (mapped, unmapped). Unmapped issues keep their element key and carry no criterion."""
    mapped: list[MappedIssue] = []
    unmapped: list[KeyedIssue] = []
    seen_unmapped: set[str] = set()
    for issue in raw_issues:
        key = element_key(capture.html, issue.element)
        criteria = criteria_for(issue, matrix)
        if criteria:
            mapped += [MappedIssue(issue, key, c) for c in criteria]
            continue
        iid = issue_id(key, issue.criterion, issue.role, issue.rule_id)
        if iid not in seen_unmapped:
            seen_unmapped.add(iid)
            unmapped.append(
                KeyedIssue(**issue.model_dump(exclude={"schema_version"}), element_key=key, id=iid)
            )
    return mapped, unmapped
