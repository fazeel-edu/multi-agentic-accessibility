"""Project directory layout. Only `store` resolves project paths."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"
DATA_DIR = PROJECT_ROOT / "data"
RESULTS_DIR = PROJECT_ROOT / "results"
CAPTURES_DIR = DATA_DIR / "captures"
VENDOR_DIR = PROJECT_ROOT / "vendor"
