import importlib.util
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
