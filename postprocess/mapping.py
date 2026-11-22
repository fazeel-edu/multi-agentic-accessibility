"""Step 1: resolve element keys and assign criteria. The only place a criterion is assigned (AD-10)."""

from dataclasses import dataclass

from contract.capture import Capture
from contract.element_key import ElementKey
from contract.enums import Role
from contract.matrix import CriteriaMatrix
from contract.models import Issue, KeyedIssue, issue_id
from tools.element import element_key

# Roles whose criteria are limited to their matrix subset. Synthesis and axe are not.
ROLE_SUBSET_ENFORCED = frozenset(
    {
        Role.SCREEN_READER,
        Role.KEYBOARD,
        Role.COLOUR_VISUAL,
        Role.COGNITIVE,
        Role.PLAIN_LANGUAGE,
        Role.WCAG_STRUCTURE,
    }
)


@dataclass(frozen=True)
class MappedIssue:
    """One reported issue bound to one criterion and one resolved element."""

    issue: Issue
    element_key: ElementKey
    criterion: str


def criteria_for(issue: Issue, matrix: CriteriaMatrix) -> list[str]:
    """Criteria an issue maps to, deterministically.

    A criterion the reporter gave counts only when the matrix lists it and, for the six Roles, only
    when it is in that Role's own subset. Otherwise a native rule_id expands through the matrix
    (one rule may yield several criteria). Anything else maps to none (the unmapped list).
    """
    if issue.criterion is not None:
        entry = matrix.entry(issue.criterion)
        in_scope = entry is not None and (
            issue.role not in ROLE_SUBSET_ENFORCED or issue.role in entry.roles
        )
        if in_scope:
            return [issue.criterion]
    if issue.rule_id is not None:
        return matrix.criteria_for_rule(issue.rule_id)
    return []


def map_issues(
    raw_issues: list[Issue], capture: Capture, matrix: CriteriaMatrix
) -> tuple[list[MappedIssue], list[KeyedIssue]]:
    """Return (mapped, unmapped). Unmapped issues keep their element key and carry no criterion."""
    mapped: list[MappedIssue] = []
    unmapped: dict[str, KeyedIssue] = {}
    for issue in raw_issues:
        key = element_key(capture.html, issue.element)
        criteria = criteria_for(issue, matrix)
        if criteria:
            mapped += [MappedIssue(issue, key, c) for c in criteria]
            continue
        iid = issue_id(key, issue.criterion, issue.role, issue.rule_id)
        keyed = KeyedIssue(**issue.model_dump(exclude={"schema_version"}), element_key=key, id=iid)
        rank = (issue.evidence, issue.description, issue.suggested_fix)
        held = unmapped.get(iid)
        if held is None or rank < (held.evidence, held.description, held.suggested_fix):
            unmapped[iid] = keyed  # same id: keep one, the same whatever the input order
    return mapped, [unmapped[i] for i in sorted(unmapped)]
