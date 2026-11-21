"""Block key-shaped strings in the given files (used by the pre-commit hook)."""

import re
import sys
from pathlib import Path

PATTERNS = [
    re.compile(r"sk-ant-[A-Za-z0-9_\-]{8,}"),
    re.compile(r"sk-[A-Za-z0-9]{32,}"),
    re.compile(r"ANTHROPIC_API_KEY\s*[=:]\s*['\"]?[A-Za-z0-9_\-]{16,}"),
]


def find_secrets(text: str) -> list[str]:
    return [m.group(0)[:12] + "..." for p in PATTERNS for m in p.finditer(text)]


def main(paths: list[str]) -> int:
    failed = False
    for name in paths:
        path = Path(name)
        if not path.is_file():
            continue
        try:
            hits = find_secrets(path.read_text(errors="ignore"))
        except OSError:
            continue
        if hits:
            failed = True
            print(f"key-shaped string in {name}: {hits[0]}", file=sys.stderr)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
