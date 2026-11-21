"""Severity and rank: one documented rule shared by every system (AD-10, FR17).

Severity (code-set, never agent-set)
    The default severity of the criterion in the Criteria Matrix. The matrix defaults are:
    CRITICAL for 2.1.1 and 2.1.2 (a user cannot proceed), SERIOUS for other level-A criteria,
    MODERATE for level-AA criteria. Severity does not depend on which system or how many
    Roles reported the issue.

Rank (1 = most important), sort key in order
    1. severity, highest first
    2. confidence, highest first (more Roles agree)
    3. criterion type: R (rule-checkable) before M before J
    4. criterion, ascending (string order of the dotted number)
    5. element key JSON, ascending (stable tie-break)
    Ties are impossible after step 5 because (element key, criterion) is unique per issue.
"""

from dataclasses import dataclass

from contract.enums import IssueType, Severity

TYPE_ORDER = {IssueType.R: 0, IssueType.M: 1, IssueType.J: 2}


@dataclass(frozen=True)
class RankInput:
    severity: Severity
    confidence: int
    issue_type: IssueType
    criterion: str
    element_key_json: str


def sort_key(item: RankInput) -> tuple:
    return (
        -int(item.severity),
        -item.confidence,
        TYPE_ORDER[item.issue_type],
        item.criterion,
        item.element_key_json,
    )


def rank_positions(items: list[RankInput]) -> list[int]:
    """Rank (1-based) for each item, in the order the items were given."""
    order = sorted(range(len(items)), key=lambda i: sort_key(items[i]))
    ranks = [0] * len(items)
    for position, index in enumerate(order, start=1):
        ranks[index] = position
    return ranks
