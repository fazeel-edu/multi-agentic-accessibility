"""Version strings recorded in every Run."""

from pathlib import Path


def bundled_cli_version(sdk_package_dir: Path) -> str:
    """Version of the Claude Code CLI bundled inside the Agent SDK wheel, or 'unknown'."""
    path = sdk_package_dir / "_bundled" / "claude.version"
    try:
        return path.read_text(encoding="utf-8").strip() or "unknown"
    except (OSError, UnicodeDecodeError):
        return "unknown"
