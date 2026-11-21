import pytest

from cli.main import main
from contract.capture import CaptureManifest
from store import captures as sc


def manifest(blocked=0):
    return CaptureManifest(
        page_id="p-01",
        capture_hash="a" * 64,
        source="p.html",
        viewport=(1280, 800),
        artifacts=[],
        versions={},
        blocked_requests=blocked,
        created_at="2026-11-21T10:00:00+00:00",
    )


def test_capture_prints_page_id_and_hash(monkeypatch, capsys, tmp_path):
    seen = {}

    def fake(page, page_id):
        seen["args"] = (str(page), page_id)
        return manifest()

    monkeypatch.setattr("capture.capture.capture_page", fake)
    assert main(["capture", "x.html", "--page-id", "p-01"]) == 0
    assert capsys.readouterr().out == f"p-01 {'a' * 64}\n"
    assert seen["args"] == ("x.html", "p-01")


def test_blocked_requests_produce_a_warning(monkeypatch, capsys):
    monkeypatch.setattr("capture.capture.capture_page", lambda page, page_id: manifest(blocked=2))
    assert main(["capture", "x.html"]) == 0
    assert "2 remote or out-of-folder requests were blocked" in capsys.readouterr().err


def test_missing_page_exits_1_with_error_line(capsys, tmp_path):
    assert main(["capture", str(tmp_path / "none.html")]) == 1
    assert capsys.readouterr().err.startswith("error: page file not found")


def test_invalid_page_id_exits_1(capsys, tmp_path):
    page = tmp_path / "p.html"
    page.write_text("<html></html>")
    assert main(["capture", str(page), "--page-id", "../x"]) == 1
    assert "invalid page_id" in capsys.readouterr().err


def test_unknown_command_is_a_usage_error():
    with pytest.raises(SystemExit):
        main(["nope"])


def test_capture_error_is_a_contract_error():
    assert issubclass(sc.CaptureError, Exception)
