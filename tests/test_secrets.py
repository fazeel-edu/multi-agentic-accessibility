import os

import pytest

from auditors.role_auditor import sdk_runner
from contract.errors import MissingApiKeyError
from store import secrets


def fake_key():
    return "sk-" + "ant-" + "x" * 20  # built at runtime so the secret scanner stays quiet


def test_reads_key_from_file(tmp_path):
    f = tmp_path / ".env.systemc"
    f.write_text(f"# note\nOTHER=1\nANTHROPIC_API_KEY = '{fake_key()}'\n")
    assert secrets.read_api_key(f) == fake_key()


@pytest.mark.parametrize(
    "text", ["", "ANTHROPIC_API_KEY=\n", "# ANTHROPIC_API_KEY=abc\n", "NOPE=1\n"]
)
def test_empty_or_missing_value_is_none(tmp_path, text):
    f = tmp_path / "e"
    f.write_text(text)
    assert secrets.read_api_key(f) is None
    assert secrets.read_api_key(tmp_path / "absent") is None


def test_api_key_prefers_env_then_file_and_never_touches_os_environ(tmp_path, monkeypatch):
    f = tmp_path / ".env.systemc"
    f.write_text(f"ANTHROPIC_API_KEY={fake_key()}\n")
    import store.secrets as s

    monkeypatch.setattr(s, "SECRETS_FILE", f)
    orig = s.read_api_key
    monkeypatch.setattr(s, "read_api_key", lambda: orig(f))
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert sdk_runner.api_key() == fake_key()
    assert "ANTHROPIC_API_KEY" not in os.environ  # not exported
    monkeypatch.setenv("ANTHROPIC_API_KEY", "from-env")
    assert sdk_runner.api_key() == "from-env"


def test_missing_key_message_names_the_file(tmp_path, monkeypatch):
    import store.secrets as s

    monkeypatch.setattr(s, "read_api_key", lambda path=None: None)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(MissingApiKeyError, match=".env.systemc"):
        sdk_runner.api_key()


def test_example_template_is_tracked_and_holds_no_key():
    from store.paths import PROJECT_ROOT

    assert (
        (PROJECT_ROOT / ".env.systemc.example").read_text().strip().endswith("ANTHROPIC_API_KEY=")
    )
