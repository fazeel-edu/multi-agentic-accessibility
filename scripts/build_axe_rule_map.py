"""Fill `severity` defaults and `rule_ids` in config/criteria_matrix.json from axe-core's rule list.

Run after changing the matrix or the vendored axe version:
    uv run python scripts/build_axe_rule_map.py

A rule maps to a criterion when its tags name that success criterion (for example `wcag143`)
and it is enabled by one of the WCAG tags the Capture runs (A, AA, 2.1, 2.2).
"""

import json
from pathlib import Path

from playwright.sync_api import sync_playwright

from capture.capture import AXE_TAGS
from store.vendor import axe_source

MATRIX = Path(__file__).resolve().parent.parent / "config" / "criteria_matrix.json"
# Failures that stop a user outright; every other A-level criterion is SERIOUS, AA is MODERATE.
CRITICAL = {"2.1.1", "2.1.2"}


def sc_tag(criterion: str) -> str:
    return "wcag" + criterion.replace(".", "")


def main() -> None:
    data = json.loads(MATRIX.read_text())
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        page.set_content("<html><body></body></html>")
        page.evaluate("(s) => { (0, eval)(s); }", axe_source())
        rules = page.evaluate("axe.getRules()")
        browser.close()
    for entry in data["criteria"]:
        tag = sc_tag(entry["criterion"])
        entry["rule_ids"] = sorted(
            r["ruleId"] for r in rules if tag in r["tags"] and set(AXE_TAGS) & set(r["tags"])
        )
        entry["severity"] = (
            4 if entry["criterion"] in CRITICAL else (3 if entry["level"] == "A" else 2)
        )
    MATRIX.write_text(json.dumps(data, indent=2) + "\n")


if __name__ == "__main__":
    main()
