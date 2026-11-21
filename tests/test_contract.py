import json
from pathlib import Path

import pytest
from pydantic import TypeAdapter, ValidationError

from contract import (
    AgentOutput,
    AuditResult,
    ElementKey,
    GroundTruthItem,
    Issue,
    KeyedIssue,
    MergedIssue,
    NodeKey,
    NodesKey,
    PageGroundTruth,
    PageKey,
    Report,
    Role,
    Run,
    Severity,
    UnresolvedKey,
    issue_id,
)
from contract.schema import export_schemas

ROOT = Path(__file__).resolve().parent.parent
KEY = TypeAdapter(ElementKey)


def agent_issue(**over):
    base = {"role": "screen_reader", "evidence": "alt is 'image123.png'", "description": "Bad alt"}
    return {**base, **over}


def test_role_is_closed_enum_of_eight():
    assert {r.value for r in Role} == {
        "screen_reader",
        "keyboard",
        "colour_visual",
        "cognitive",
        "plain_language",
        "wcag_structure",
        "inclusive_design",
        "axe_core",
    }
    with pytest.raises(ValidationError):
        Issue.model_validate(agent_issue(role="oracle"))


def test_severity_is_ordinal():
    assert Severity.MINOR < Severity.MODERATE < Severity.SERIOUS < Severity.CRITICAL
    assert Severity(3) is Severity.SERIOUS


@pytest.mark.parametrize(
    "field,value",
    [
        ("confidence", 3),
        ("severity", 3),
        ("rank", 1),
        ("grounded", True),
        ("roles", ["keyboard"]),
        ("element_key", {"kind": "page"}),
        ("id", "abc"),
    ],
)
def test_agent_input_rejects_code_set_fields(field, value):
    with pytest.raises(ValidationError):
        Issue.model_validate(agent_issue(**{field: value}))


def test_issue_requires_evidence_and_valid_criterion():
    with pytest.raises(ValidationError):
        Issue.model_validate(agent_issue(evidence="  "))
    with pytest.raises(ValidationError):
        Issue.model_validate(agent_issue(criterion="1.1"))
    assert Issue.model_validate(agent_issue(criterion="2.4.11")).criterion == "2.4.11"


def test_element_may_be_absent():
    assert Issue.model_validate(agent_issue()).element is None


def test_element_key_union_roundtrip_and_equality():
    for key in (
        NodeKey(path="html>body>a[1]"),
        NodesKey(paths=("a", "b")),
        PageKey(),
        UnresolvedKey(raw="#nope"),
    ):
        assert KEY.validate_json(KEY.dump_json(key)) == key
    assert NodeKey(path="a") == NodeKey(path="a")
    assert NodeKey(path="a") != PageKey()
    assert hash(NodeKey(path="a")) == hash(NodeKey(path="a"))


def test_issue_id_is_stable_and_distinguishes_inputs():
    k = NodeKey(path="html>body>img[1]")
    a = issue_id(k, "1.1.1", Role.SCREEN_READER)
    assert a == issue_id(k, "1.1.1", Role.SCREEN_READER)
    assert a != issue_id(k, "1.1.1", Role.KEYBOARD)
    assert a != issue_id(k, "2.4.4", Role.SCREEN_READER)


def merged(**over):
    base = {
        "id": "x",
        "element_key": {"kind": "node", "path": "a"},
        "criterion": "1.1.1",
        "roles": ["screen_reader"],
        "confidence": 1,
        "severity": 3,
        "rank": 1,
        "grounded": True,
        "evidence": ["e"],
        "description": "d",
    }
    return {**base, **over}


def test_merged_issue_bounds():
    assert MergedIssue.model_validate(merged()).severity is Severity.SERIOUS
    for bad in (
        {"confidence": 0},
        {"confidence": 7},
        {"rank": 0},
        {"severity": 9},
        {"criterion": None},
    ):
        with pytest.raises(ValidationError):
            MergedIssue.model_validate(merged(**bad))


def test_report_has_required_fields():
    fields = set(Report.model_fields)
    assert {
        "cannot_test_statement",
        "priority_notes",
        "role_status",
        "run_id",
        "system",
        "phase",
        "group_id",
        "capture_hash",
        "config_hash",
        "postprocess_version",
    } <= fields
    with pytest.raises(ValidationError):
        Report.model_validate(
            {
                "run_id": "r",
                "system": "axe",
                "page_id": "p",
                "phase": "dev",
                "group_id": "g",
                "capture_hash": "c",
                "config_hash": "h",
                "postprocess_version": "1",
                "role_status": [],
                "cannot_test_statement": "",
            }
        )


def test_ground_truth_item():
    item = GroundTruthItem.model_validate(
        {
            "page_id": "forms-01",
            "element_key": {"kind": "node", "path": "a"},
            "acceptable_criteria": ["2.4.4", "2.4.6"],
            "affected_user_group": "screen_reader",
            "severity": 3,
            "issue_type": "J",
        }
    )
    assert item.scope.value == "element"
    with pytest.raises(ValidationError):
        GroundTruthItem.model_validate({**item.model_dump(mode="json"), "acceptable_criteria": []})


def test_every_top_level_model_carries_schema_version():
    for model in (
        Issue,
        KeyedIssue,
        AgentOutput,
        MergedIssue,
        GroundTruthItem,
        PageGroundTruth,
        AuditResult,
        Run,
        Report,
    ):
        assert model.model_fields["schema_version"].default == "1", model


def test_models_are_frozen():
    issue = Issue.model_validate(agent_issue())
    with pytest.raises(ValidationError):
        issue.evidence = "changed"


def test_committed_schemas_match_models():
    exported = export_schemas()
    assert "issue_v1.json" in exported
    for name, schema in exported.items():
        on_disk = json.loads((ROOT / "contract" / "schemas" / name).read_text())
        assert on_disk == schema, f"{name} stale: run scripts/export_schemas.py"


def test_issue_schema_has_no_code_set_fields():
    props = export_schemas()["issue_v1.json"]["properties"]
    assert not {"confidence", "severity", "rank", "grounded", "roles", "element_key", "id"} & set(
        props
    )
    assert "schema_version" in props


def test_report_keeps_unmapped_issues_apart_from_merged_issues():
    unmapped = KeyedIssue.model_validate(
        {
            **agent_issue(),
            "element_key": {"kind": "page"},
            "id": "abc",
        }
    )
    report = Report.model_validate(
        {
            "run_id": "r",
            "system": "axe",
            "page_id": "p",
            "phase": "dev",
            "group_id": "g",
            "capture_hash": "c",
            "config_hash": "h",
            "postprocess_version": "1",
            "role_status": [],
            "cannot_test_statement": "x",
            "unmapped_issues": [unmapped.model_dump(mode="json")],
        }
    )
    assert report.issues == [] and report.unmapped_issues[0].criterion is None


def test_capture_manifest_ids_are_constrained():
    from contract.capture import CaptureManifest

    base = {
        "page_id": "p-01",
        "capture_hash": "a" * 64,
        "source": "p.html",
        "viewport": (1, 1),
        "artifacts": [],
        "versions": {},
        "created_at": "t",
    }
    assert CaptureManifest.model_validate(base)
    for bad in ({"page_id": "../x"}, {"capture_hash": "g" * 64}, {"capture_hash": "a" * 63}):
        with pytest.raises(ValidationError):
            CaptureManifest.model_validate({**base, **bad})
