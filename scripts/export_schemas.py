"""Write contract/schemas/*.json from the models. Run: uv run python scripts/export_schemas.py"""

import json
from pathlib import Path

from contract.schema import export_schemas

OUT = Path(__file__).resolve().parent.parent / "contract" / "schemas"

if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    for name, schema in export_schemas().items():
        (OUT / name).write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n")
