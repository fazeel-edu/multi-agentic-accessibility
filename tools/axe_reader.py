"""Reader of the axe-core results stored in a Capture. Pure; never runs axe."""

from typing import Any

from contract.capture import Capture


def _nodes(nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "selector": n["target"][0] if n["target"] else None,
            "html": n.get("html", "")[:200],
            "failure": (n.get("failureSummary") or "")[:300],
        }
        for n in nodes
    ]


def _rows(results: list[dict[str, Any]], rule_id: str | None) -> list[dict[str, Any]]:
    return [
        {
            "rule_id": r["id"],
            "impact": r.get("impact"),
            "description": r["description"],
            "tags": [t for t in r["tags"] if t.startswith("wcag")],
            "nodes": _nodes(r["nodes"]),
        }
        for r in results
        if rule_id is None or r["id"] == rule_id
    ]


def violations(capture: Capture, rule_id: str | None = None) -> list[dict[str, Any]]:
    return _rows(capture.axe_results.get("violations", []), rule_id)


def needs_review(capture: Capture, rule_id: str | None = None) -> list[dict[str, Any]]:
    """axe results it could not decide; a Role may judge them, they are not scored."""
    return _rows(capture.axe_results.get("needs_review", []), rule_id)
