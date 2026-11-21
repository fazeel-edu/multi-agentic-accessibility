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


def write(root, f=None, **kw):
    args = {
        "source": "p.html",
        "viewport": (1280, 800),
        "versions": {"axe-core": "4.14.1"},
        "blocked_requests": 0,
        "created_at": "2026-11-21T10:00:00+00:00",
        "root": root,
    }
    return sc.write_capture("p-01", f or files(), **{**args, **kw})


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
