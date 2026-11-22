"""Pure tool registry: one entry per analysis tool a Role may use. SDK wrappers are built from this
in auditors; nothing here imports an SDK, a browser or the network."""

import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from contract.capture import Capture
from tools import axe_reader, contrast, focus_trace, readability
from tools.element import element_text


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    properties: dict[str, dict[str, Any]]  # JSON Schema properties
    required: tuple[str, ...]
    run: Callable[[Capture, dict[str, Any]], str]

    @property
    def input_schema(self) -> dict[str, Any]:
        return {"type": "object", "properties": self.properties, "required": list(self.required)}


def _json(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True)


def _axe_violations(c: Capture, a: dict[str, Any]) -> str:
    return _json(axe_reader.violations(c, a.get("rule_id")))


def _axe_needs_review(c: Capture, a: dict[str, Any]) -> str:
    return _json(axe_reader.needs_review(c, a.get("rule_id")))


def _focus_trace(c: Capture, a: dict[str, Any]) -> str:
    return _json(focus_trace.summarize(c))


def _contrast_check(c: Capture, a: dict[str, Any]) -> str:
    try:
        return _json(
            contrast.check(
                a["foreground"], a["background"], a.get("font_size_px", 16), a.get("bold", False)
            )
        )
    except ValueError as exc:
        return _json({"error": str(exc)})


def _contrast_failures(c: Capture, a: dict[str, Any]) -> str:
    try:
        return _json(contrast.failing_rows(c, a.get("selector")))
    except ValueError as exc:
        return _json({"error": str(exc)})


def _readability(c: Capture, a: dict[str, Any]) -> str:
    text = a.get("text")
    if text is None and a.get("selector"):
        text = element_text(c.html, a["selector"])
        if text is None:
            return _json({"error": f"selector {a['selector']!r} matches no element"})
    if text is None:
        return _json({"error": "give `text` or `selector`"})
    return _json(readability.score(text))


_RULE = {"rule_id": {"type": "string", "description": "only this axe rule id (optional)"}}

TOOLS: dict[str, ToolSpec] = {
    t.name: t
    for t in (
        ToolSpec(
            "axe_violations",
            "axe-core violations stored in the Capture (WCAG 2.2 AA rules).",
            _RULE,
            (),
            _axe_violations,
        ),
        ToolSpec(
            "axe_needs_review",
            "axe-core results it could not decide; judge them yourself.",
            _RULE,
            (),
            _axe_needs_review,
        ),
        ToolSpec(
            "focus_trace",
            "Keyboard focus order, hidden or covered focus, and dialog behaviour from the scripted trace.",
            {},
            (),
            _focus_trace,
        ),
        ToolSpec(
            "contrast_check",
            "Contrast ratio of two colours (#rrggbb or rgb(r, g, b)) and whether it passes WCAG 1.4.3.",
            {
                "foreground": {"type": "string"},
                "background": {"type": "string"},
                "font_size_px": {"type": "number"},
                "bold": {"type": "boolean"},
            },
            ("foreground", "background"),
            _contrast_check,
        ),
        ToolSpec(
            "contrast_failures",
            "Text elements measured in the Capture that fail their contrast requirement.",
            {"selector": {"type": "string", "description": "only this element (optional)"}},
            (),
            _contrast_failures,
        ),
        ToolSpec(
            "readability",
            "Flesch reading ease and grade level for text, or for the text of an element.",
            {"text": {"type": "string"}, "selector": {"type": "string"}},
            (),
            _readability,
        ),
    )
}
