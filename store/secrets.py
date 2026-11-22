"""Reads the project-level API key file. The key is returned, never exported to os.environ."""

from pathlib import Path

from store.paths import PROJECT_ROOT

KEY_NAME = "ANTHROPIC_API_KEY"
SECRETS_FILE = PROJECT_ROOT / ".env.systemc"


def read_api_key(path: Path = SECRETS_FILE) -> str | None:
    """The value of ANTHROPIC_API_KEY in the file, or None if the file or value is absent."""
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    for line in text.splitlines():
        line = line.strip().removeprefix("export ").lstrip()
        if line.startswith("#") or "=" not in line:
            continue
        name, _, value = line.partition("=")
        if name.strip() == KEY_NAME:
            value = value.strip()
            if value and value[0] in "\"'":
                value = value[1:].split(value[0])[0]
            else:
                value = value.split(" #")[0].strip()
            return value or None
    return None
