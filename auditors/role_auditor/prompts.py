"""Builds a Role's prompts from its Role Spec, the Criteria Matrix subset and the Capture. Pure."""

import json

from contract.capture import Capture
from contract.enums import Role
from contract.matrix import CriteriaMatrix
from contract.models import Issue
from contract.role_spec import RoleSpecFile
from tools.element import visible_text


def criteria_for_role(matrix: CriteriaMatrix, role: Role) -> list[str]:
    return [f"{e.criterion} {e.name}" for e in matrix.criteria if role in e.roles]


def system_prompt(spec: RoleSpecFile, matrix: CriteriaMatrix) -> str:
    parts = [spec.prompt, "Guidance:\n" + spec.guidance]
    criteria = criteria_for_role(matrix, spec.role)
    if criteria:
        parts.append(
            "Your WCAG 2.2 criteria (report only these):\n" + "\n".join(f"- {c}" for c in criteria)
        )
    for i, ex in enumerate(spec.examples, start=1):
        parts.append(
            f"Example {i} ({ex.kind.value}):\nSituation: {ex.situation}\nAnswer:\n{ex.output}"
        )
    return "\n\n".join(parts)


def _axe_summary(capture: Capture) -> str:
    rows = {
        key: sorted({r["id"] for r in capture.axe_results.get(key, [])})
        for key in ("violations", "needs_review")
    }
    return json.dumps(rows, indent=2)


def _section(name: str, capture: Capture) -> str:
    match name:
        case "accessibility_tree":
            return capture.accessibility_tree
        case "html":
            return capture.html
        case "computed_styles":
            return json.dumps(capture.computed_styles, indent=1, sort_keys=True)
        case "focus_trace":
            return "Use the focus_trace tool; the raw trace is not pasted here."
        case "visible_text":
            return visible_text(capture.html)
        case "axe_summary":
            return _axe_summary(capture)
    raise ValueError(f"unknown input {name!r}")


def _inputs(spec: RoleSpecFile, capture: Capture) -> str:
    return "\n\n".join(f"## {name}\n{_section(name, capture)}" for name in spec.inputs)


def user_prompt(spec: RoleSpecFile, capture: Capture) -> str:
    """Only the inputs the Role Spec names, in its order."""
    return _inputs(spec, capture) + "\n\nAudit this page now and answer with the JSON object only."


def synthesis_user_prompt(
    spec: RoleSpecFile, capture: Capture, outputs: dict[Role, list[Issue]], failed: list[Role]
) -> str:
    """The Synthesis Agent sees all role outputs (and which roles failed), nothing else about roles."""
    body = {
        role.value: [i.model_dump(mode="json", exclude={"schema_version"}) for i in issues]
        for role, issues in outputs.items()
    }
    return (
        _inputs(spec, capture)
        + "\n\n## role_outputs\n"
        + json.dumps(body, indent=2)
        + ("\n\n## failed_roles\n" + ", ".join(r.value for r in failed) if failed else "")
        + "\n\nSynthesise now and answer with the JSON object only."
    )


def estimate_tokens(*texts: str) -> int:
    """Rough size: characters / 4. Recorded in the Run, not billed."""
    return sum(len(t) for t in texts) // 4
