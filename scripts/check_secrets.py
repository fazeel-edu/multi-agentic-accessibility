"""Block key-shaped strings (used by the pre-commit hook).

    check_secrets.py FILE...            scan files in the working tree
    check_secrets.py --staged PATH...   scan the staged (index) version of each path

Fails closed: a file that cannot be read counts as a failure, not a pass.
"""

import re
import subprocess
import sys
from pathlib import Path

PATTERNS = [
    re.compile(r"sk-ant-[A-Za-z0-9_\-]{8,}"),
    re.compile(r"sk-[A-Za-z0-9_\-]{32,}"),
    re.compile(r"ANTHROPIC_API_KEY\s*[=:]\s*['\"]?[A-Za-z0-9_\-]{16,}"),
]


def find_secrets(text: str) -> list[str]:
    return [m.group(0)[:12] + "..." for p in PATTERNS for m in p.finditer(text)]


def _working_tree(name: str) -> str:
    return Path(name).read_text(encoding="utf-8", errors="ignore")


def _staged(name: str) -> str:
    out = subprocess.run(
        ["git", "show", f":{name}"], capture_output=True, check=True
    )  # bytes: the exact staged blob
    return out.stdout.decode("utf-8", errors="ignore")


def main(args: list[str]) -> int:
    staged = bool(args) and args[0] == "--staged"
    paths = args[1:] if staged else args
    read = _staged if staged else _working_tree
    failed = False
    for name in paths:
        try:
            text = read(name)
        except (OSError, subprocess.CalledProcessError) as exc:
            failed = True
            print(f"cannot scan {name}: {exc}", file=sys.stderr)
            continue
        hits = find_secrets(text)
        if hits:
            failed = True
            print(f"key-shaped string in {name}: {hits[0]}", file=sys.stderr)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
