import importlib.util
import subprocess
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "check_secrets", Path(__file__).resolve().parent.parent / "scripts" / "check_secrets.py"
)
check_secrets = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(check_secrets)


def test_detects_anthropic_key(tmp_path):
    f = tmp_path / "a.txt"
    f.write_text("key = " + "sk-" + "ant-api03-abcdefghijklmnop")
    assert check_secrets.main([str(f)]) == 1


def test_detects_env_assignment(tmp_path):
    f = tmp_path / "b.txt"
    f.write_text("ANTHROPIC_API" + "_KEY=abcdefghijklmnopqrstuvwx")
    assert check_secrets.main([str(f)]) == 1


def test_clean_file_passes(tmp_path):
    f = tmp_path / "c.txt"
    f.write_text("read ANTHROPIC_API_KEY from the environment")
    assert check_secrets.main([str(f)]) == 0


def test_detects_generic_and_hyphenated_provider_keys(tmp_path):
    for text in ("sk-" + "a" * 40, "sk-" + "proj-" + "A1b2" * 10):
        f = tmp_path / "k.txt"
        f.write_text(text)
        assert check_secrets.main([str(f)]) == 1


def test_unreadable_file_fails_closed(tmp_path):
    assert check_secrets.main([str(tmp_path / "missing.txt")]) == 1


def test_staged_mode_scans_the_index_not_the_working_copy(tmp_path, monkeypatch):
    def git(*args):
        subprocess.run(["git", *args], cwd=tmp_path, check=True, capture_output=True)

    git("init", "-q")
    f = tmp_path / "with space.txt"
    f.write_text("key = " + "sk-" + "ant-api03-abcdefghijklmnop")
    git("add", "with space.txt")
    f.write_text("clean now")  # working copy differs from what is staged
    monkeypatch.chdir(tmp_path)
    assert check_secrets.main(["--staged", "with space.txt"]) == 1
    git("reset", "-q")
    assert check_secrets.main(["--staged", "with space.txt"]) == 1  # no longer staged: cannot scan
