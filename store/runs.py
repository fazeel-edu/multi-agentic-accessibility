"""Run storage (AD-9): run.json, issues.jsonl, tool_calls.jsonl written once; reports are derived."""

from pathlib import Path

from contract.enums import System
from contract.errors import ContractError
from contract.models import AuditResult, Issue, Report, Run, ToolCall
from store.paths import RESULTS_DIR

_SAFE = frozenset("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.")


class RunStoreError(ContractError):
    """A Run cannot be written or read."""


def run_dir(system: System, page_id: str, run_id: str, root: Path = RESULTS_DIR) -> Path:
    for part in (page_id, run_id):
        if not part or part.startswith(".") or not set(part) <= _SAFE:
            raise RunStoreError(f"unsafe id {part!r}")
    return root / system.value / page_id / run_id


def _write_new(path: Path, text: str) -> None:
    try:
        with open(path, "x", encoding="utf-8") as f:  # never overwrite
            f.write(text)
    except FileExistsError as exc:
        raise RunStoreError(f"{path.name} already exists and is never rewritten") from exc


def write_run(run: Run, result: AuditResult, root: Path = RESULTS_DIR) -> Path:
    """Write the three immutable Run files. `run` carries role status, notes, usage and seconds."""
    directory = run_dir(run.system, run.page_id, run.run_id, root)
    try:
        directory.mkdir(parents=True, exist_ok=False)
    except FileExistsError as exc:
        raise RunStoreError(f"run {run.run_id} already exists") from exc
    _write_new(directory / "run.json", run.model_dump_json(indent=2) + "\n")
    _write_new(
        directory / "issues.jsonl",
        "".join(i.model_dump_json() + "\n" for i in result.raw_issues + result.needs_review),
    )
    _write_new(
        directory / "tool_calls.jsonl",
        "".join(c.model_dump_json() + "\n" for c in result.tool_calls),
    )
    return directory


def read_run(
    system: System, page_id: str, run_id: str, root: Path = RESULTS_DIR
) -> tuple[Run, AuditResult]:
    """Rebuild the Run and its AuditResult from the stored files, for recomputing a Report."""
    directory = run_dir(system, page_id, run_id, root)
    try:
        run = Run.model_validate_json((directory / "run.json").read_text(encoding="utf-8"))
        issues = [
            Issue.model_validate_json(line)
            for line in (directory / "issues.jsonl").read_text(encoding="utf-8").splitlines()
        ]
        calls = [
            ToolCall.model_validate_json(line)
            for line in (directory / "tool_calls.jsonl").read_text(encoding="utf-8").splitlines()
        ]
    except (OSError, ValueError) as exc:
        raise RunStoreError(f"cannot read run {run_id}: {exc}") from exc
    review = system is System.AXE
    result = AuditResult(
        raw_issues=[] if review else issues,
        needs_review=issues if review else [],
        role_status=run.role_status,
        priority_notes=run.priority_notes,
        usage=run.usage,
        seconds=run.seconds,
        tool_calls=calls,
    )
    return run, result


def write_report(report: Report, root: Path = RESULTS_DIR) -> Path:
    """Write the derived `report.{postprocess_version}.json` once; a new version is a new file."""
    directory = run_dir(report.system, report.page_id, report.run_id, root)
    path = directory / f"report.{report.postprocess_version}.json"
    _write_new(path, report.model_dump_json(indent=2) + "\n")
    return path
