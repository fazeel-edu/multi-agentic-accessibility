"""Shared test helpers."""

from pathlib import Path

import pytest

from contract.capture import ALL_ARTIFACTS, ArtifactEntry, Capture, CaptureManifest
from contract.enums import Phase, System
from contract.models import Run

ROOT = Path(__file__).resolve().parent.parent
FIXTURE_HTML = (ROOT / "data/pages/fixture-01.html").read_text()


def make_capture(html: str = FIXTURE_HTML, **parts) -> Capture:
    """A Capture built in memory (no browser). Pass axe_results, focus_trace, contrast, ..."""
    manifest = CaptureManifest(
        page_id="t-01",
        capture_hash="a" * 64,
        source="t.html",
        viewport=(1280, 800),
        artifacts=[
            ArtifactEntry(name=n, sha256="0" * 64, size=0, in_capture_hash=False)
            for n in ALL_ARTIFACTS
        ],
        versions={},
        created_at="2026-11-21T10:00:00+00:00",
    )
    return Capture(
        manifest=manifest,
        html=html,
        computed_styles=parts.get("computed_styles", {}),
        accessibility_tree=parts.get("accessibility_tree", ""),
        axe_results=parts.get("axe_results", {"violations": [], "needs_review": [], "passes": []}),
        focus_trace=parts.get("focus_trace", {}),
        contrast=parts.get("contrast", []),
        screenshot_file="screenshot.png",
    )


def make_run(system: System = System.ROLE_MULTI_AGENT) -> Run:
    return Run(
        run_id="r-1",
        system=system,
        page_id="t-01",
        phase=Phase.DEV,
        group_id="g-1",
        config_hash="c" * 64,
        capture_hash="a" * 64,
        started_at="2026-11-21T10:00:00+00:00",
    )


@pytest.fixture(scope="session")
def fixture_capture(tmp_path_factory):
    """The real fixture-01 Capture, taken once with Chromium (skips if it is not installed)."""
    from playwright.sync_api import Error as PlaywrightError

    from capture.capture import capture_page
    from store import captures

    root = tmp_path_factory.mktemp("fixture-capture")
    try:
        manifest = capture_page(ROOT / "data/pages/fixture-01.html", root=root)
    except captures.CaptureError as exc:
        if "browser error" in str(exc):
            pytest.skip("Chromium not installed")
        raise
    except PlaywrightError:
        pytest.skip("Chromium not installed")
    return captures.read_capture(manifest.page_id, manifest.capture_hash, root)
