import json
from functools import partial

import pytest

from cli import main as cli
from contract.enums import Phase, Role, System
from contract.models import AuditResult, Issue, Run
from store import captures, runs
from store.runs import RunStoreError
from tests.conftest import make_run
from tests.fakes import FakeRunner, answer, issue


def sample():
    run = make_run()
    result = AuditResult(
        raw_issues=[
            Issue(
                role=Role.SCREEN_READER,
                element="#hero",
                criterion="1.1.1",
                evidence="e",
                description="d",
            )
        ],
        role_status=[],
        priority_notes=["n"],
        seconds=1.5,
    )
    return run, result


def test_run_files_written_once_and_read_back(tmp_path):
    run, result = sample()
    d = runs.write_run(run, result, tmp_path)
    assert d == tmp_path / "role_multi_agent" / "t-01" / "r-1"
    assert sorted(p.name for p in d.iterdir()) == ["issues.jsonl", "run.json", "tool_calls.jsonl"]
    assert json.loads((d / "issues.jsonl").read_text().splitlines()[0])["criterion"] == "1.1.1"
    run2, result2 = runs.read_run(System.ROLE_MULTI_AGENT, "t-01", "r-1", tmp_path)
    assert run2 == run and result2.raw_issues == result.raw_issues
    with pytest.raises(RunStoreError):
        runs.write_run(run, result, tmp_path)


def test_reports_are_versioned_and_never_rewritten(tmp_path):
    from postprocess import run as postprocess
    from store.config import load
    from tests.conftest import make_capture

    run, result = sample()
    runs.write_run(run, result, tmp_path)
    report = postprocess(result, make_capture(), load().config.matrix, run)
    path = runs.write_report(report, tmp_path)
    assert path.name == "report.1.json"
    with pytest.raises(RunStoreError):
        runs.write_report(report, tmp_path)


@pytest.mark.parametrize("bad", ["../x", "", ".hidden", "a/b"])
def test_unsafe_ids_rejected(tmp_path, bad):
    with pytest.raises(RunStoreError):
        runs.run_dir(System.AXE, bad, "r", tmp_path)


# --- audit command -----------------------------------------------------------------------


@pytest.fixture
def env(tmp_path, monkeypatch, fixture_capture):
    from store import paths, terms

    monkeypatch.setattr(paths, "RESULTS_DIR", tmp_path)
    m = fixture_capture.manifest
    monkeypatch.setattr(captures, "capture_hashes", lambda page_id: [m.capture_hash])
    monkeypatch.setattr(captures, "read_capture", lambda page_id, h: fixture_capture)
    monkeypatch.setattr(runs, "write_run", partial(runs.write_run, root=tmp_path))
    monkeypatch.setattr(runs, "write_report", partial(runs.write_report, root=tmp_path))
    monkeypatch.setattr(terms, "require_provider_terms", lambda: "2026-11-20")
    return tmp_path


def fake(monkeypatch):
    runner = FakeRunner(
        {
            Role.SCREEN_READER: [answer("screen_reader", issue("#hero", "1.1.1"))],
            Role.PLAIN_LANGUAGE: [answer("plain_language", issue("#more-1", "2.4.4"))],
            Role.INCLUSIVE_DESIGN: [
                answer(
                    "inclusive_design",
                    issue("#more-1", "2.4.4", derived_from=["plain_language"]),
                    notes=["links first"],
                )
            ],
        }
    )
    monkeypatch.setattr(cli, "make_runner", lambda: runner)
    return runner


def test_audit_stores_a_run_and_a_readable_report(env, monkeypatch, capsys, fixture_capture):
    runner = fake(monkeypatch)
    assert cli.main(["audit", "fixture-01", "--group-id", "g-9"]) == 0
    out = capsys.readouterr().out
    assert "7 sessions" in out and "SDK estimate" in out and "complete" in out
    run_dir = next((env / "role_multi_agent" / "fixture-01").iterdir())
    assert sorted(p.name for p in run_dir.iterdir()) == [
        "issues.jsonl",
        "report.1.json",
        "run.json",
        "tool_calls.jsonl",
    ]
    run = Run.model_validate_json((run_dir / "run.json").read_text())
    assert (
        run.group_id == "g-9" and run.phase is Phase.DEV and run.provider_terms_date == "2026-11-20"
    )
    assert run.capture_hash == fixture_capture.manifest.capture_hash and len(run.config_hash) == 64
    assert run.model_id == "claude-haiku-5-5" and "claude-agent-sdk" in run.versions
    assert len(run.role_status) == 7 and run.priority_notes == ["links first"]
    report = json.loads((run_dir / "report.1.json").read_text())
    pairs = {(i["criterion"], tuple(i["roles"])) for i in report["issues"]}
    assert ("1.1.1", ("screen_reader",)) in pairs and ("2.4.4", ("plain_language",)) in pairs
    assert len(runner.requests) == 7 and (env / "ledger-dev.jsonl").exists()


def test_audit_refuses_without_dated_provider_terms(tmp_path, monkeypatch, capsys):
    from store import paths

    monkeypatch.setattr(paths, "RESULTS_DIR", tmp_path)
    runner = fake(monkeypatch)
    assert cli.main(["audit", "fixture-01"]) == 1
    assert "Read on" in capsys.readouterr().err and runner.requests == []


def test_audit_without_api_key_fails_cleanly(env, monkeypatch, capsys):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert cli.main(["audit", "fixture-01"]) == 1
    assert "ANTHROPIC_API_KEY" in capsys.readouterr().err


def test_audit_records_ablation_variant_and_failed_roles(env, monkeypatch, capsys):
    runner = fake(monkeypatch)
    assert cli.main(["audit", "fixture-01", "--exclude", "cognitive"]) == 0
    run_dir = next((env / "role_multi_agent" / "fixture-01").iterdir())
    run = Run.model_validate_json((run_dir / "run.json").read_text())
    assert run.variant == [Role.COGNITIVE] and Role.COGNITIVE not in runner.roles_started()


def test_audit_unknown_page(env, monkeypatch, capsys):
    fake(monkeypatch)
    monkeypatch.setattr(captures, "capture_hashes", lambda page_id: [])
    assert cli.main(["audit", "nope"]) == 1
    assert "systemc capture" in capsys.readouterr().err
