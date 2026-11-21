"""Integration tests that drive real Chromium. Skipped when the browser is not installed."""

import socket
from pathlib import Path

import pytest
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright

from capture.capture import capture_page
from contract.capture import ALL_ARTIFACTS, HASHED_ARTIFACTS
from contract.element_key import NodeKey
from store import captures as sc
from tools.element import element_key

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "data/pages/fixture-01.html"


def _browser_available() -> bool:
    try:
        with sync_playwright() as pw:
            pw.chromium.launch(headless=True).close()
        return True
    except PlaywrightError:
        return False


pytestmark = pytest.mark.skipif(not _browser_available(), reason="Chromium not installed")


@pytest.fixture(scope="module")
def captured(tmp_path_factory):
    root = tmp_path_factory.mktemp("captures")
    manifest = capture_page(FIXTURE, root=root)
    return root, manifest, sc.read_capture(manifest.page_id, manifest.capture_hash, root)


def test_manifest_lists_every_artifact_and_versions(captured):
    _, manifest, _ = captured
    assert manifest.page_id == "fixture-01" and manifest.source == "fixture-01.html"
    assert [a.name for a in manifest.artifacts] == list(ALL_ARTIFACTS)
    assert {a.name for a in manifest.artifacts if a.in_capture_hash} == set(HASHED_ARTIFACTS)
    assert manifest.versions["axe-core"] == "4.14.1"
    assert {"playwright", "chromium", "focus_script"} <= set(manifest.versions)
    assert manifest.blocked_requests == 0


def test_recapture_of_unchanged_page_gives_same_hash(captured, tmp_path):
    _, manifest, _ = captured
    assert capture_page(FIXTURE, root=tmp_path).capture_hash == manifest.capture_hash


def test_reading_a_capture_makes_no_network_request(captured, monkeypatch):
    root, manifest, _ = captured

    def boom(*a, **k):
        raise AssertionError("network access while reading a Capture")

    monkeypatch.setattr(socket.socket, "connect", boom)
    monkeypatch.setattr(socket, "getaddrinfo", boom)
    assert sc.read_capture(manifest.page_id, manifest.capture_hash, root).html


def test_remote_requests_are_blocked_and_counted(tmp_path):
    page = tmp_path / "remote.html"
    page.write_text(
        '<!DOCTYPE html><html lang="en"><head><title>t</title></head><body><main>'
        '<img src="http://203.0.113.1/x.png" alt="x"></main></body></html>'
    )
    assert capture_page(page, root=tmp_path / "c").blocked_requests >= 1


def test_axe_runs_with_wcag22_tags_and_keeps_needs_review(captured):
    _, _, cap = captured
    axe = cap.axe_results
    assert {v["id"] for v in axe["violations"]} == {"color-contrast"}
    assert axe["violations"][0]["nodes"][0]["target"] == ["#shipping-note"]
    assert "needs_review" in axe and "incomplete" not in axe
    assert "timestamp" not in axe and "url" not in axe
    assert set(axe["toolOptions"]["runOnly"]["values"]) >= {"wcag22aa", "wcag2aa"}


def test_contrast_measures_the_planted_defect(captured):
    _, _, cap = captured
    key = element_key(cap.html, "#shipping-note")
    row = next(r for r in cap.contrast if r["path"] == key.path)
    assert row["ratio"] == 2.78 and row["passes"] is False
    assert [r["path"] for r in cap.contrast if not r["passes"]] == [key.path]


def test_style_and_contrast_paths_match_tools_element_paths(captured):
    _, _, cap = captured
    for path in list(cap.computed_styles) + [r["path"] for r in cap.contrast]:
        assert element_key(cap.html, path) == NodeKey(path=path), path


def test_accessibility_tree_present(captured):
    _, _, cap = captured
    assert 'link "Skip to main content"' in cap.accessibility_tree
    assert 'heading "Harbor H5 wireless headphones"' in cap.accessibility_tree


def test_focus_trace_forward_order(captured):
    _, _, cap = captured
    ids = [s["id"] for s in cap.focus_trace["tab_forward"] if s["id"]]
    assert ids == [
        "size-btn",
        "more-1",
        "more-2",
        "more-3",
        "more-4",
        "more-5",
        "jump-terms",
        "email",
        "fullname",
        "promo",
        "phone",
        "pay",
        "terms-link",
    ]
    assert all(s["focus_indicator"] != "none" for s in cap.focus_trace["tab_forward"])


def test_focus_trace_shows_focus_hidden_behind_sticky_header(captured):
    _, _, cap = captured
    covered = {s["id"] for s in cap.focus_trace["tab_backward"] if s["obscured_points"] > 0}
    assert {"more-1", "more-2", "more-3"} <= covered
    assert not any(s["obscured_points"] for s in cap.focus_trace["tab_forward"])


def test_dialog_probe_shows_focus_not_moved_into_dialog(captured):
    _, _, cap = captured
    opened = [p for p in cap.focus_trace["dialog_probes"] if p["opened"]]
    assert len(opened) == 1
    probe = opened[0]
    assert probe["dialog"] == element_key(cap.html, "#size-guide").path
    assert probe["focus_after_open"]["inside_dialog"] is False
    assert probe["focus_after_tab"]["inside_dialog"] is False


def test_missing_page_raises(tmp_path):
    with pytest.raises(sc.CaptureError):
        capture_page(tmp_path / "none.html", root=tmp_path)
