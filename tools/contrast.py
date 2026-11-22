"""Contrast calculator and reader of the contrast measurements stored in a Capture. Pure."""

import re
from typing import Any

from contract.capture import Capture
from contract.element_key import NodeKey, NodesKey
from tools.element import element_key

_HEX = re.compile(r"^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")
_RGB = re.compile(
    r"^rgba?\(\s*(\d{1,3})[ ,]+(\d{1,3})[ ,]+(\d{1,3})(?:\s*[,/]\s*([\d.]+%?))?\s*\)$"
)


def parse_color(value: str) -> tuple[int, int, int]:
    """Parse `#rgb`, `#rrggbb`, `rgb(r, g, b)` or `rgba(...)`. Raises ValueError otherwise."""
    text = value.strip()
    if m := _HEX.match(text):
        h = m.group(1)
        h = "".join(c * 2 for c in h) if len(h) == 3 else h
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    if m := _RGB.match(text):
        r, g, b = (int(x) for x in m.groups()[:3])
        alpha = m.group(4)
        if alpha is not None:
            value = float(alpha[:-1]) / 100 if alpha.endswith("%") else float(alpha)
            if value < 1:
                raise ValueError(f"{value:g} alpha: give the opaque colour it is drawn over")
        if max(r, g, b) <= 255:
            return r, g, b
    raise ValueError(f"unsupported colour {value!r}: use #rrggbb or rgb(r, g, b)")


def _luminance(rgb: tuple[int, int, int]) -> float:
    def lin(v: int) -> float:
        c = v / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (lin(v) for v in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(foreground: str, background: str) -> float:
    hi, lo = sorted(
        (_luminance(parse_color(foreground)), _luminance(parse_color(background))), reverse=True
    )
    return round((hi + 0.05) / (lo + 0.05), 2)


def check(
    foreground: str, background: str, font_size_px: float = 16, bold: bool = False
) -> dict[str, Any]:
    """WCAG 1.4.3 check: 4.5:1, or 3:1 for large text (24px, or 18.66px and bold)."""
    ratio = contrast_ratio(foreground, background)
    large = font_size_px >= 24 or (font_size_px >= 18.66 and bold)
    required = 3.0 if large else 4.5
    return {"ratio": ratio, "required": required, "large_text": large, "passes": ratio >= required}


def failing_rows(capture: Capture, selector: str | None = None) -> list[dict[str, Any]]:
    """Measured text elements below the required ratio; optionally only for one selector."""
    rows = [r for r in capture.contrast if not r["passes"]]
    if selector is not None:
        key = element_key(capture.html, selector)
        if isinstance(key, NodeKey):
            wanted = {key.path}
        elif isinstance(key, NodesKey):
            wanted = set(key.paths)
        else:
            raise ValueError(f"selector {selector!r} matches no element")
        rows = [r for r in rows if r["path"] in wanted]
    return rows
