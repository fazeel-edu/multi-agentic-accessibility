import random

import pytest

from contract.element_key import NodeKey, NodesKey, PageKey
from contract.enums import IssueType, Role, RoleState, Severity, System
from contract.matrix import CriteriaMatrix
from contract.models import AuditResult, Issue, RoleStatus
from postprocess import CANNOT_TEST_STATEMENT, POSTPROCESS_VERSION, run
from postprocess.rank import RankInput, rank_positions, sort_key
from store.config import load
from tests.conftest import make_capture, make_run

MATRIX = load().config.matrix
CAPTURE = make_capture()


def issue(role="screen_reader", element="#hero", criterion="1.1.1", rule_id=None, **kw):
    return Issue(
        role=role,
        element=element,
        criterion=criterion,
        rule_id=rule_id,
        evidence=kw.pop("evidence", f"{role} saw it"),
        description=kw.pop("description", f"{role} desc"),
        **kw,
    )


def report(*issues, system=System.ROLE_MULTI_AGENT, **kw):
    result = AuditResult(raw_issues=list(issues), role_status=kw.pop("role_status", []), **kw)
    return run(result, CAPTURE, MATRIX, make_run(system))


def test_same_element_via_css_and_xpath_merges_and_counts_distinct_roles():
    r = report(
        issue("screen_reader", "#hero", "2.4.1"),
        issue("keyboard", '//img[@id="hero"]', "2.4.1"),
        issue("screen_reader", "main section img:first-of-type", "2.4.1"),
    )
    assert len(r.issues) == 1
    merged = r.issues[0]
    assert merged.roles == [Role.KEYBOARD, Role.SCREEN_READER]  # sorted
    assert merged.confidence == 2
    assert isinstance(merged.element_key, NodeKey) and merged.grounded
    assert len(merged.evidence) == 2


def test_different_criterion_or_element_do_not_merge():
    r = report(
        issue(element="#hero"),
        issue(element="#hero", criterion="1.3.1"),
        issue(element="#fit-photo"),
    )
    assert len(r.issues) == 3


def test_synthesis_never_adds_a_voter():
    r = report(
        issue("screen_reader"),
        issue("inclusive_design", derived_from=["screen_reader"], description="pattern"),
    )
    assert r.issues[0].roles == [Role.SCREEN_READER] and r.issues[0].confidence == 1
    assert r.issues[0].derived_from == ["screen_reader"]


def test_synthesis_only_issue_has_one_voice():
    r = report(issue("inclusive_design", derived_from=["keyboard"]))
    assert r.issues[0].roles == [Role.INCLUSIVE_DESIGN] and r.issues[0].confidence == 1


def test_confidence_is_set_by_code_from_distinct_roles():
    roles = ["screen_reader", "plain_language", "cognitive"]  # the roles that own 2.4.6
    r = report(*[issue(role, criterion="2.4.6") for role in roles])
    assert r.issues[0].confidence == 3


def test_axe_rule_ids_expand_through_the_matrix():
    r = report(
        issue("axe_core", "#shipping-note", None, "color-contrast"),
        issue("axe_core", "#hero", None, "image-alt"),
        issue("axe_core", "#more-1", None, "link-name"),  # one rule, two criteria
    )
    pairs = {(i.criterion, i.confidence) for i in r.issues}
    assert pairs == {("1.4.3", 1), ("1.1.1", 1), ("2.4.4", 1), ("4.1.2", 1)}
    assert all(i.roles == [Role.AXE_CORE] for i in r.issues)


def test_same_pipeline_same_report_shape_for_a_and_c():
    a = report(issue("axe_core", "#hero", None, "image-alt"), system=System.AXE)
    c = report(issue("screen_reader", "#hero"), system=System.ROLE_MULTI_AGENT)
    assert type(a) is type(c) and a.system is System.AXE
    assert a.issues[0].criterion == c.issues[0].criterion


def test_issues_with_no_criterion_go_to_unmapped_not_to_ranking():
    r = report(
        issue(criterion=None, rule_id="not-a-rule", element="#hero"),
        issue(criterion="1.4.12", element="#hero"),  # outside the matrix
        issue(criterion=None, rule_id=None, element="#hero"),
        issue(criterion=None, rule_id="not-a-rule", element="#hero"),  # duplicate of the first
    )
    assert r.issues == []
    assert len(r.unmapped_issues) == 3
    assert all(
        u.id and u.element_key == r.unmapped_issues[0].element_key for u in r.unmapped_issues
    )


def test_grounded_only_for_resolved_elements():
    r = report(
        issue(element="#hero"),
        issue(element="#nope", criterion="1.3.1"),
        issue(element=None, criterion="2.4.2"),
        issue("axe_core", "a", None, "document-title"),  # many nodes
    )
    by = {(i.criterion, i.element_key.kind): i for i in r.issues}
    assert by[("1.1.1", "node")].grounded
    assert not by[("1.3.1", "unresolved")].grounded
    assert not by[("2.4.2", "page")].grounded
    assert (
        isinstance(by[("2.4.2", "nodes")].element_key, NodesKey) and by[("2.4.2", "nodes")].grounded
    )
    assert isinstance(PageKey(), PageKey)


def test_severity_comes_from_the_matrix_not_the_reporter():
    r = report(issue("keyboard", "#size-guide", "2.1.2"), issue("screen_reader", "#hero", "2.4.6"))
    by = {i.criterion: i.severity for i in r.issues}
    assert by == {"2.1.2": Severity.CRITICAL, "2.4.6": Severity.MODERATE}


def test_report_carries_run_fields_statement_notes_and_role_status():
    status = [RoleStatus(role=Role.KEYBOARD, state=RoleState.OK)]
    r = report(issue(), priority_notes=["fix forms first"], role_status=status)
    assert (r.run_id, r.page_id, r.group_id, r.capture_hash) == ("r-1", "t-01", "g-1", "a" * 64)
    assert r.config_hash == "c" * 64 and r.postprocess_version == POSTPROCESS_VERSION
    assert (
        r.cannot_test_statement == CANNOT_TEST_STATEMENT
        and "not a compliance certificate" in CANNOT_TEST_STATEMENT
    )
    assert r.priority_notes == ["fix forms first"] and r.role_status == status


def test_postprocess_is_pure_and_input_order_does_not_change_the_report():
    issues = [
        issue("screen_reader", "#hero"),
        issue("keyboard", "#hero", "2.4.1"),
        issue("cognitive", "#fullname", criterion="3.3.2"),
        issue("axe_core", "#shipping-note", None, "color-contrast"),
        issue("plain_language", "#more-1", criterion="2.4.4"),
        issue(criterion=None, rule_id="zzz"),
    ]
    baseline = report(*issues)
    for seed in range(5):
        shuffled = issues[:]
        random.Random(seed).shuffle(shuffled)
        assert report(*shuffled) == baseline
    assert [i.rank for i in baseline.issues] == list(range(1, len(baseline.issues) + 1))
    assert report(*issues) == baseline


# --- rank rule ---------------------------------------------------------------


def ri(sev=2, conf=1, typ=IssueType.M, crit="1.1.1", key="a"):
    return RankInput(Severity(sev), conf, typ, crit, key)


def test_rank_orders_by_severity_then_confidence_then_type_then_criterion_then_key():
    items = [
        ri(sev=2),
        ri(sev=4),
        ri(sev=2, conf=3),
        ri(sev=2, typ=IssueType.R),
        ri(sev=2, typ=IssueType.J),
        ri(sev=2, crit="0.0.1"),
        ri(sev=2, key="0"),
    ]
    ordered = [items[i] for i in sorted(range(len(items)), key=lambda i: sort_key(items[i]))]
    assert ordered[0].severity is Severity.CRITICAL
    assert ordered[1].confidence == 3
    sev2 = [i for i in ordered if i.severity == 2 and i.confidence == 1]
    assert [i.issue_type for i in sev2 if i.criterion == "1.1.1" and i.element_key_json == "a"] == [
        IssueType.R,
        IssueType.M,
        IssueType.J,
    ]
    assert sort_key(ri(crit="0.0.1")) < sort_key(
        ri(typ=IssueType.M, crit="1.1.1")
    )  # same type: criterion
    assert sort_key(ri(key="0")) < sort_key(ri(key="a"))


@pytest.mark.parametrize("n", [0, 1, 5])
def test_rank_positions_are_a_permutation_of_one_to_n(n):
    items = [ri(sev=1 + i % 4, key=str(i)) for i in range(n)]
    assert sorted(rank_positions(items)) == list(range(1, n + 1))


def test_matrix_has_severity_and_rules_for_every_entry():
    assert isinstance(MATRIX, CriteriaMatrix)
    assert all(e.severity in set(Severity) for e in MATRIX.criteria)
    assert MATRIX.criteria_for_rule("color-contrast") == ["1.4.3"]
    assert MATRIX.criteria_for_rule("link-name") == ["2.4.4", "4.1.2"]
    assert MATRIX.criteria_for_rule("nope") == []


def test_out_of_subset_criterion_goes_to_unmapped_not_ranked():
    r = report(issue("keyboard", "#hero", "1.1.1"), issue("screen_reader", "#hero", "1.1.1"))
    assert [i.roles for i in r.issues] == [[Role.SCREEN_READER]]
    assert [(u.role, u.criterion) for u in r.unmapped_issues] == [(Role.KEYBOARD, "1.1.1")]


def test_out_of_scope_criterion_falls_through_to_the_rule_id():
    r = report(issue("axe_core", "#hero", "9.9.9", "image-alt"))
    assert [i.criterion for i in r.issues] == ["1.1.1"]


def test_synthesis_and_axe_may_use_any_matrix_criterion():
    r = report(
        issue("inclusive_design", "#hero", "2.1.1", derived_from=["keyboard"]),
        issue("axe_core", "#hero", "3.3.2"),
    )
    assert {i.criterion for i in r.issues} == {"2.1.1", "3.3.2"}


def test_a_reporting_role_supplies_the_merged_text_not_the_synthesis_echo():
    r = report(
        issue(
            "inclusive_design",
            "#hero",
            "1.1.1",
            description="aaa pattern",
            derived_from=["screen_reader"],
        ),
        issue("screen_reader", "#hero", "1.1.1", description="the real description"),
    )
    assert r.issues[0].description == "the real description"
    assert r.issues[0].evidence[0] == "screen_reader saw it"
