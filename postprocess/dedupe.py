"""Step 2: merge on (element_key, criterion); Confidence = number of distinct reporting Roles."""

from collections import defaultdict

from contract.element_key import NodeKey, NodesKey
from contract.enums import Role
from contract.models import merged_id
from postprocess.mapping import MappedIssue


def group(mapped: list[MappedIssue]) -> dict[tuple[str, str], list[MappedIssue]]:
    """Group by (element key as JSON, criterion), keeping first-seen order."""
    groups: dict[tuple[str, str], list[MappedIssue]] = defaultdict(list)
    for m in mapped:
        groups[(m.element_key.model_dump_json(), m.criterion)].append(m)
    return dict(groups)


def voters(members: list[MappedIssue]) -> list[Role]:
    """Sorted distinct reporting Roles. The Synthesis Agent (inclusive_design) echoes other
    Roles' findings and never adds a voter. A group only synthesis reported has one voice."""
    roles = {m.issue.role for m in members} - {Role.INCLUSIVE_DESIGN}
    if not roles:
        return [Role.INCLUSIVE_DESIGN]
    return sorted(roles, key=lambda r: r.value)


def confidence(roles: list[Role]) -> int:
    return len(roles)


def is_grounded(member: MappedIssue) -> bool:
    """The cited element exists in the Capture (AD-10): a node or a set of nodes."""
    return isinstance(member.element_key, NodeKey | NodesKey)


def merged_key_id(member: MappedIssue) -> str:
    return merged_id(member.element_key, member.criterion)
