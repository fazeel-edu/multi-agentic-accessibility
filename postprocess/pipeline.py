"""postprocess.run: AuditResult -> Report. Pure; same code for System A and System C."""

from contract.capture import Capture
from contract.matrix import CriteriaMatrix
from contract.models import AuditResult, MergedIssue, Report, Run
from postprocess import dedupe
from postprocess.mapping import map_issues
from postprocess.rank import RankInput, rank_positions

POSTPROCESS_VERSION = "1"

CANNOT_TEST_STATEMENT = (
    "This report is guidance, not a compliance certificate. It cannot test: real assistive "
    "technology (screen readers are simulated from the page's accessibility tree), page states "
    "the Capture did not reach (logged-in views, multi-step flows, hover and timed content), "
    "audio and video (captions, transcripts), motion and animation, layouts at other viewport "
    "sizes or zoom levels, or the experience of real people with disabilities."
)


def run(
    audit_result: AuditResult, capture: Capture, matrix: CriteriaMatrix, run_meta: Run
) -> Report:
    """Map, de-duplicate, set Confidence, severity, rank and grounded; build the Report."""
    mapped, unmapped = map_issues(audit_result.raw_issues, capture, matrix)
    groups = dedupe.group(mapped)

    drafts = []
    for members in groups.values():
        first = members[0]
        entry = matrix.entry(first.criterion)
        roles = dedupe.voters(members)
        drafts.append((members, first, entry, roles))

    ranks = rank_positions(
        [
            RankInput(
                severity=entry.severity,
                confidence=dedupe.confidence(roles),
                issue_type=entry.type,
                criterion=first.criterion,
                element_key_json=first.element_key.model_dump_json(),
            )
            for _, first, entry, roles in drafts
        ]
    )

    issues = []
    for (members, first, entry, roles), rank in zip(drafts, ranks, strict=True):
        by_role = sorted(members, key=lambda m: m.issue.role.value)
        evidence = list(dict.fromkeys(m.issue.evidence for m in by_role))
        derived = list(dict.fromkeys(d for m in by_role for d in m.issue.derived_from))
        issues.append(
            MergedIssue(
                id=dedupe.merged_key_id(first),
                element_key=first.element_key,
                criterion=first.criterion,
                roles=roles,
                confidence=dedupe.confidence(roles),
                severity=entry.severity,
                rank=rank,
                grounded=dedupe.is_grounded(first),
                evidence=evidence,
                description=by_role[0].issue.description,
                suggested_fix=next(
                    (m.issue.suggested_fix for m in by_role if m.issue.suggested_fix), ""
                ),
                derived_from=derived,
            )
        )
    issues.sort(key=lambda i: i.rank)

    return Report(
        run_id=run_meta.run_id,
        system=run_meta.system,
        page_id=run_meta.page_id,
        phase=run_meta.phase,
        group_id=run_meta.group_id,
        capture_hash=run_meta.capture_hash,
        config_hash=run_meta.config_hash,
        postprocess_version=POSTPROCESS_VERSION,
        role_status=audit_result.role_status,
        cannot_test_statement=CANNOT_TEST_STATEMENT,
        priority_notes=audit_result.priority_notes,
        issues=issues,
        unmapped_issues=unmapped,
    )
