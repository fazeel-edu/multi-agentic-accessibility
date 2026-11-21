"""Only `store` opens project files (spine rule). Static check for obvious file I/O calls."""

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OTHER_PACKAGES = [
    "config",
    "contract",
    "capture",
    "tools",
    "auditors",
    "postprocess",
    "eval",
    "review",
    "cli",
    "tools_dev",
]
IO_NAMES = {"open", "read_text", "read_bytes", "write_text", "write_bytes"}


def io_calls(source: str) -> list[str]:
    hits = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Call):
            f = node.func
            name = (
                f.id if isinstance(f, ast.Name) else f.attr if isinstance(f, ast.Attribute) else ""
            )
            if name in IO_NAMES:
                hits.append(name)
    return hits


def test_no_file_io_outside_store():
    problems = [
        f"{p.relative_to(ROOT)}: {n}"
        for pkg in OTHER_PACKAGES
        for p in (ROOT / pkg).rglob("*.py")
        for n in io_calls(p.read_text())
    ]
    assert not problems, "\n".join(problems)


def test_checker_detects_io():
    assert io_calls("from pathlib import Path\nPath('a').read_text()") == ["read_text"]
    assert io_calls("open('f')") == ["open"]
    assert io_calls("x = 1") == []
