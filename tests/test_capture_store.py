import json
from pathlib import Path

import pytest

from contract import capture as cap
from store import captures as sc


def files(**over):
    base = {name: f"content of {name}".encode() for name in cap.ALL_ARTIFACTS}
    base[cap.STYLES] = b"{}"
    base[cap.AXE] = b"{}"
    base[cap.FOCUS] = b"{}"
    base[cap.CONTRAST] = b"[]"
    return {**base, **over}


def write(root, f=None, page_id="p-01", **kw):
    args = {
        "source": "p.html",
        "viewport": (1280, 800),
        "versions": {"axe-core": "4.14.1"},
        "blocked_requests": 0,
        "created_at": "2026-11-21T10:00:00+00:00",
        "root": root,
    }
    return sc.write_capture(page_id, f or files(), **{**args, **kw})


def test_write_then_read_roundtrip(tmp_path):
    m = write(tmp_path)
    loaded = sc.read_capture("p-01", m.capture_hash, tmp_path)
    assert loaded.html == "content of page.html"
    assert loaded.manifest.versions["axe-core"] == "4.14.1"
    assert {a.name for a in m.artifacts} == set(cap.ALL_ARTIFACTS)
    assert {a.name for a in m.artifacts if a.in_capture_hash} == set(cap.HASHED_ARTIFACTS)
    assert sc.capture_hashes("p-01", tmp_path) == [m.capture_hash]


def test_hash_ignores_screenshot_contrast_and_timestamp(tmp_path):
    a = write(tmp_path / "a")
    b = write(
        tmp_path / "b",
        files(**{cap.SCREENSHOT: b"other pixels", cap.CONTRAST: b"[1]"}),
        created_at="2030-01-01T00:00:00+00:00",
    )
    assert a.capture_hash == b.capture_hash


@pytest.mark.parametrize("name", cap.HASHED_ARTIFACTS)
def test_hash_changes_with_each_hashed_artifact(tmp_path, name):
    assert (
        write(tmp_path / "a").capture_hash
        != write(tmp_path / "b", files(**{name: b"changed"})).capture_hash
    )


def test_existing_capture_is_never_rewritten(tmp_path):
    first = write(tmp_path)
    second = write(tmp_path, created_at="2031-01-01T00:00:00+00:00")
    assert second.created_at == first.created_at
    assert second == first


def test_missing_artifact_rejected(tmp_path):
    f = files()
    del f[cap.AXE]
    with pytest.raises(sc.CaptureError):
        write(tmp_path, f)
    assert not list(tmp_path.rglob("capture.json"))


def test_tampered_artifact_detected(tmp_path):
    m = write(tmp_path)
    (sc.capture_dir("p-01", m.capture_hash, tmp_path) / cap.HTML).write_text("edited")
    with pytest.raises(sc.CaptureError):
        sc.read_capture("p-01", m.capture_hash, tmp_path)


def test_unknown_capture_raises(tmp_path):
    with pytest.raises(sc.CaptureError):
        sc.read_capture("nope", "0" * 64, tmp_path)
    assert sc.capture_hashes("nope", tmp_path) == []


def test_interrupted_write_is_not_a_capture(tmp_path):
    m = write(tmp_path)
    target = sc.capture_dir("p-01", m.capture_hash, tmp_path)
    (target / sc.MANIFEST).unlink()
    assert sc.capture_hashes("p-01", tmp_path) == []
    assert write(tmp_path).capture_hash == m.capture_hash  # rewritten cleanly


@pytest.mark.parametrize("bad", ["../x", "a/b", ".hidden", "", "/abs", "a b"])
def test_page_id_that_could_leave_the_root_is_rejected(tmp_path, bad):
    with pytest.raises(sc.CaptureError):
        write(tmp_path, page_id=bad)
    with pytest.raises(sc.CaptureError):
        sc.capture_hashes(bad, tmp_path)
    assert not list(tmp_path.rglob("*"))


@pytest.mark.parametrize("bad", ["../" + "a" * 61, "A" * 64, "g" * 64, "a" * 63])
def test_capture_hash_must_be_64_lowercase_hex(tmp_path, bad):
    with pytest.raises(sc.CaptureError):
        sc.capture_dir("p-01", bad, tmp_path)


def test_staging_folder_is_never_listed_as_a_capture(tmp_path):
    m = write(tmp_path)
    stale = tmp_path / "p-01" / ".capture-abc123"
    stale.mkdir()
    (stale / sc.MANIFEST).write_text("{}")
    assert sc.capture_hashes("p-01", tmp_path) == [m.capture_hash]


def test_manifest_with_missing_artifact_raises_capture_error_not_keyerror(tmp_path):
    m = write(tmp_path)
    path = sc.capture_dir("p-01", m.capture_hash, tmp_path) / sc.MANIFEST
    data = json.loads(path.read_text())
    data["artifacts"] = data["artifacts"][:-1]
    path.write_text(json.dumps(data))
    with pytest.raises(sc.CaptureError, match="expected artifacts"):
        sc.read_capture("p-01", m.capture_hash, tmp_path)


def test_losing_a_same_hash_race_keeps_the_finished_capture(tmp_path, monkeypatch):
    first = write(tmp_path)
    target = sc.capture_dir("p-01", first.capture_hash, tmp_path)
    marker = target / "marker"
    marker.write_text("x")
    real_exists = Path.exists
    calls = {"n": 0}

    def exists(self):  # the early "already there?" check misses; the second check sees it
        if self == target / sc.MANIFEST:
            calls["n"] += 1
            return calls["n"] > 1
        return real_exists(self)

    monkeypatch.setattr(Path, "exists", exists)
    again = write(tmp_path)
    assert again.capture_hash == first.capture_hash
    assert marker.exists()  # the finished Capture was not deleted
    assert not [p for p in (tmp_path / "p-01").iterdir() if p.name.startswith(".capture-")]


def test_vendored_axe_matches_the_pinned_version():
    from store.paths import VENDOR_DIR
    from store.vendor import AXE_VERSION

    head = (VENDOR_DIR / "axe-core" / "axe.min.js").read_text()[:200]
    assert f"axe v{AXE_VERSION}" in head
