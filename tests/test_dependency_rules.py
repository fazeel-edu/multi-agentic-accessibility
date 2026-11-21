"""Enforce the spine's dependency graph by parsing imports (AST)."""

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

PACKAGES = {
    "config",
    "contract",
    "capture",
    "tools",
    "auditors",
    "postprocess",
    "eval",
    "store",
    "review",
    "cli",
    "tools_dev",
}

# Allowed project imports per package. "tools.element" is the only part of
# tools that postprocess and eval may use.
ALLOWED: dict[str, set[str]] = {
    "contract": set(),
    "config": set(),
    "tools": {"contract"},
    "store": {"contract"},
    "capture": {"store", "contract"},
    "auditors": {"tools", "store", "contract"},
    "postprocess": {"tools.element", "contract"},
    "eval": {"tools.element", "contract", "store"},
    "review": {"store", "contract"},
    "cli": {"auditors", "capture", "postprocess", "eval", "review", "store", "contract", "tools"},
    "tools_dev": {"contract", "tools", "store"},
}


def _targets(tree: ast.AST) -> list[str]:
    """Dotted project-module names imported by a parsed module."""
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found += [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            found.append(node.module)
            found += [f"{node.module}.{a.name}" for a in node.names]
    return [t for t in found if t.split(".")[0] in PACKAGES]


def _permitted(owner: str, target: str) -> bool:
    top = target.split(".")[0]
    if top == owner:
        return True
    allowed = ALLOWED[owner]
    if top in allowed:
        return True
    return any(target == a or target.startswith(a + ".") for a in allowed if "." in a)


def violations(owner: str, source: str) -> list[str]:
    """Imports in `source` (belonging to package `owner`) that break the graph."""
    bad = []
    for target in _targets(ast.parse(source)):
        top = target.split(".")[0]
        if _permitted(owner, target):
            continue
        # `from tools import element` yields both `tools` and `tools.element`;
        # the bare package form is fine when the submodule form is allowed.
        if (
            any(
                a.startswith(top + ".") and a != target and _permitted(owner, a)
                for a in ALLOWED[owner]
            )
            and "." not in target
        ):
            continue
        bad.append(f"{owner} -> {target}")
    return bad


def test_all_packages_exist_and_import():
    for pkg in PACKAGES:
        assert (ROOT / pkg / "__init__.py").exists(), pkg
        __import__(pkg)


def test_project_follows_dependency_graph():
    problems = []
    for owner in PACKAGES:
        for path in (ROOT / owner).rglob("*.py"):
            problems += [
                f"{path.relative_to(ROOT)}: {v}" for v in violations(owner, path.read_text())
            ]
    assert not problems, "\n".join(problems)


def test_checker_rejects_eval_importing_auditors():
    assert violations("eval", "from auditors import axe_auditor")
    assert violations("eval", "import auditors.role_auditor")


def test_checker_allows_tools_element_only_for_postprocess_and_eval():
    assert violations("postprocess", "from tools.element import element_key") == []
    assert violations("eval", "from tools import element") == []
    assert violations("postprocess", "from tools.contrast import ratio")
    assert violations("eval", "import tools.focus_trace")


def test_contract_imports_nothing_in_project():
    assert violations("contract", "from store import config")
    assert violations("contract", "import pydantic") == []


def test_cli_may_import_downward():
    assert violations("cli", "from eval import match\nfrom auditors import axe_auditor") == []
    assert violations("review", "from auditors import axe_auditor")
