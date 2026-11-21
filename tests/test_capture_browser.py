"""Integration tests that drive real Chromium. Skipped when the browser is not installed."""

import json
import os
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


# Set REQUIRE_BROWSER=1 (for example in CI) to make a missing Chromium a failure, not a skip.
pytestmark = pytest.mark.skipif(
    not os.environ.get("REQUIRE_BROWSER") and not _browser_available(),
    reason="Chromium not installed",
)


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
    opened = [p for p in cap.focus_trace["dialogs"]["probes"] if p["opened"]]
    assert len(opened) == 1
    probe = opened[0]
    assert probe["dialog"] == element_key(cap.html, "#size-guide").path
    assert probe["focus_after_open"]["inside_dialog"] is False
    assert probe["focus_after_tab"]["inside_dialog"] is False


def test_missing_page_raises(tmp_path):
    with pytest.raises(sc.CaptureError):
        capture_page(tmp_path / "none.html", root=tmp_path)


def test_focus_trace_records_why_each_pass_ended(captured):
    _, _, cap = captured
    assert cap.focus_trace["script_version"] == "2"
    assert cap.focus_trace["tab_forward_end"] in {"left_document", "revisit", "cap"}
    assert cap.focus_trace["tab_backward_end"] in {"left_document", "revisit", "cap"}
    assert cap.focus_trace["dialogs"]["candidates"] == cap.focus_trace["dialogs"]["probed"] == 1


def test_focus_trace_never_stores_typed_values(tmp_path):
    page = tmp_path / "typed.html"
    page.write_text(
        '<!DOCTYPE html><html lang="en"><head><title>t</title></head><body><main>'
        '<label for="pw">Password</label><input id="pw" type="password" value="hunter2-secret">'
        '<input id="go" type="submit" value="Sign in"></main></body></html>'
    )
    manifest = capture_page(page, root=tmp_path / "c")
    cap = sc.read_capture(manifest.page_id, manifest.capture_hash, tmp_path / "c")
    text = json.dumps(cap.focus_trace)
    assert "hunter2-secret" not in text
    assert "Sign in" in text  # button-like input labels are kept


def test_files_outside_the_page_folder_are_blocked(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.png").write_bytes(b"x")
    pages = tmp_path / "pages"
    pages.mkdir()
    page = pages / "p.html"
    page.write_text(
        f'<!DOCTYPE html><html lang="en"><head><title>t</title></head><body><main>'
        f'<img src="file://{outside}/secret.png" alt="x"></main></body></html>'
    )
    assert (
        capture_page(page, root=tmp_path / "c").blocked_requests >= 1
    )  # counted once per page load


def test_a_navigating_button_does_not_abort_the_capture(tmp_path):
    page = tmp_path / "nav.html"
    page.write_text(
        '<!DOCTYPE html><html lang="en"><head><title>t</title></head><body><main>'
        '<button type="button" onclick="location.href=\'about:blank\'">Go</button>'
        "</main></body></html>"
    )
    manifest = capture_page(page, root=tmp_path / "c")
    cap = sc.read_capture(manifest.page_id, manifest.capture_hash, tmp_path / "c")
    assert cap.focus_trace["dialogs"]["probed"] == 1


def test_axe_version_mismatch_is_rejected(tmp_path, monkeypatch):
    import capture.capture as module

    monkeypatch.setattr(module, "AXE_VERSION", "0.0.0")
    with pytest.raises(sc.CaptureError, match="axe version"):
        capture_page(FIXTURE, root=tmp_path)
    assert not list(tmp_path.rglob("capture.json"))


def test_path_mismatch_between_browser_and_tools_is_rejected(tmp_path, monkeypatch):
    import capture.capture as module

    monkeypatch.setattr(module, "element_key", lambda html, path: module.NodeKey(path=path + "x"))
    with pytest.raises(sc.CaptureError, match="do not match tools.element"):
        capture_page(FIXTURE, root=tmp_path)


@pytest.mark.parametrize("bad", ["../escape", "a/b", ".hidden", "/abs"])
def test_invalid_page_id_is_rejected_before_any_browser_work(tmp_path, bad):
    with pytest.raises(sc.CaptureError, match="invalid page_id"):
        capture_page(FIXTURE, page_id=bad, root=tmp_path)
    assert not list(tmp_path.rglob("*"))
