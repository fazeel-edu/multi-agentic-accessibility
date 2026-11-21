"""Capture one local page into an immutable Capture (AD-3, FR5, FR6).

All derived artifacts (styles, contrast, axe, accessibility tree, focus trace) are computed
here, in the browser, once. Later stages read them and never launch a browser.
"""

import json
from datetime import UTC, datetime
from importlib.metadata import version as pkg_version
from pathlib import Path
from typing import Any

from playwright.sync_api import BrowserContext, Page, sync_playwright
from playwright.sync_api import Error as PlaywrightError

from capture import scripts
from contract import capture as cap
from contract.capture import CaptureManifest
from store import captures as store_captures
from store.paths import CAPTURES_DIR
from store.vendor import AXE_VERSION, axe_source

VIEWPORT = (1280, 800)
AXE_TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"]
_LOCAL_SCHEMES = ("file:", "data:", "about:", "blob:")
# Run-specific fields removed from axe output so a re-capture hashes the same.
_AXE_VOLATILE = ("timestamp", "url", "testEnvironment")


def _dump(obj: Any) -> bytes:
    return (json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


class _Network:
    """Refuses every non-local request and counts them."""

    def __init__(self) -> None:
        self.blocked = 0

    def handle(self, route) -> None:
        if route.request.url.startswith(_LOCAL_SCHEMES):
            route.continue_()
        else:
            self.blocked += 1
            route.abort()


def _open(context: BrowserContext, url: str) -> Page:
    page = context.new_page()
    page.goto(url, wait_until="load")
    page.evaluate("document.fonts.ready.then(() => true)")
    return page


def _axe(page: Page) -> tuple[dict[str, Any], str]:
    page.evaluate("(src) => { (0, eval)(src); }", axe_source())  # no DOM change
    options = {"runOnly": {"type": "tag", "values": AXE_TAGS}}
    raw = page.evaluate("(opts) => axe.run(document, opts)", options)
    detected = page.evaluate("axe.version")
    results = {k: v for k, v in raw.items() if k not in _AXE_VOLATILE}
    results["needs_review"] = results.pop("incomplete")  # axe's name for "needs review"
    return results, detected


def _tab_pass(
    context: BrowserContext, url: str, key: str, from_bottom: bool
) -> list[dict[str, Any]]:
    page = _open(context, url)
    if from_bottom:
        page.evaluate("window.scrollTo(0, document.documentElement.scrollHeight)")
    steps: list[dict[str, Any]] = []
    seen: set[str] = set()
    for step in range(1, scripts.MAX_TAB_STEPS + 1):
        page.keyboard.press(key)
        state = page.evaluate(scripts.FOCUS_STATE)
        if state is None or state["path"] in seen:
            break
        seen.add(state["path"])
        steps.append({"step": step, **state})
    page.close()
    return steps


def _dialog_probes(context: BrowserContext, url: str) -> list[dict[str, Any]]:
    page = _open(context, url)
    openers = page.evaluate(scripts.CANDIDATE_OPENERS)
    page.close()
    probes = []
    for opener in openers:
        page = _open(context, url)
        before = set(page.evaluate(scripts.VISIBLE_DIALOGS))
        probe: dict[str, Any] = {"opener": opener, "opened": False}
        try:
            page.locator("xpath=" + opener).click(timeout=2000)
        except PlaywrightError:
            probe["click_failed"] = True
            probes.append(probe)
            page.close()
            continue
        opened = [d for d in page.evaluate(scripts.VISIBLE_DIALOGS) if d not in before]
        if opened:
            focus = page.evaluate(scripts.FOCUS_STATE)
            page.keyboard.press("Tab")
            after_tab = page.evaluate(scripts.FOCUS_STATE)
            probe.update(
                opened=True,
                dialog=opened[0],
                focus_after_open=focus
                and {"path": focus["path"], "inside_dialog": focus["inside_dialog"]},
                focus_after_tab=after_tab
                and {"path": after_tab["path"], "inside_dialog": after_tab["inside_dialog"]},
            )
        probes.append(probe)
        page.close()
    return probes


def capture_page(
    page_file: Path, page_id: str | None = None, root: Path = CAPTURES_DIR
) -> CaptureManifest:
    """Capture a local HTML file. A re-capture of an unchanged page gives the same hash."""
    page_file = Path(page_file).resolve()
    if not page_file.is_file():
        raise store_captures.CaptureError(f"page file not found: {page_file.name}")
    page_id = page_id or page_file.stem
    url = page_file.as_uri()
    network = _Network()
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": VIEWPORT[0], "height": VIEWPORT[1]},
            device_scale_factor=1,
            locale="en-US",
            color_scheme="light",
            reduced_motion="reduce",
        )
        context.route("**/*", network.handle)
        page = _open(context, url)
        html = page.content()
        styles = page.evaluate(scripts.COMPUTED_STYLES)
        contrast = page.evaluate(scripts.CONTRAST)
        a11y = page.locator("html").aria_snapshot()
        screenshot = page.screenshot(full_page=True)
        axe_results, axe_found = _axe(page)  # last: injecting axe must not precede the above
        page.close()
        if axe_found != AXE_VERSION:
            raise store_captures.CaptureError(f"axe version {axe_found}, expected {AXE_VERSION}")
        focus_trace = {
            "script_version": scripts.FOCUS_SCRIPT_VERSION,
            "tab_forward": _tab_pass(context, url, "Tab", from_bottom=False),
            "tab_backward": _tab_pass(context, url, "Shift+Tab", from_bottom=True),
            "dialog_probes": _dialog_probes(context, url),
        }
        browser_version = browser.version
        context.close()
        browser.close()
    files = {
        cap.HTML: html.encode("utf-8"),
        cap.STYLES: _dump(styles),
        cap.A11Y: (a11y + "\n").encode("utf-8"),
        cap.AXE: _dump(axe_results),
        cap.FOCUS: _dump(focus_trace),
        cap.CONTRAST: _dump(contrast),
        cap.SCREENSHOT: screenshot,
    }
    return store_captures.write_capture(
        page_id,
        files,
        source=page_file.name,
        viewport=VIEWPORT,
        versions={
            "playwright": pkg_version("playwright"),
            "chromium": browser_version,
            "axe-core": axe_found,
            "focus_script": scripts.FOCUS_SCRIPT_VERSION,
        },
        blocked_requests=network.blocked,
        created_at=datetime.now(UTC).isoformat(timespec="seconds"),
        root=root,
    )
