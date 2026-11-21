"""JSON Schema export, derived from the models, never hand-written (AD-2)."""

from contract.models import GroundTruthItem, Issue, Report, Run

EXPORTED = {
    "issue_v1.json": Issue,
    "ground_truth_item_v1.json": GroundTruthItem,
    "run_v1.json": Run,
    "report_v1.json": Report,
}


def export_schemas() -> dict[str, dict]:
    return {name: model.model_json_schema() for name, model in EXPORTED.items()}
