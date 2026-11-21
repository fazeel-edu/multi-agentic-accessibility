"""Loads the Role Spec files from config/roles/ (one file per Role)."""

from pathlib import Path

from pydantic import ValidationError

from contract.enums import Role
from contract.errors import ConfigError
from contract.role_spec import RoleSpecFile
from store.paths import CONFIG_DIR

REQUIRED_ROLES = (
    Role.SCREEN_READER,
    Role.KEYBOARD,
    Role.COLOUR_VISUAL,
    Role.COGNITIVE,
    Role.PLAIN_LANGUAGE,
    Role.WCAG_STRUCTURE,
    Role.INCLUSIVE_DESIGN,
)


def load_role_specs(config_dir: Path = CONFIG_DIR) -> dict[Role, RoleSpecFile]:
    """All seven Role Specs, validated; a missing or mismatched file is a ConfigError."""
    specs: dict[Role, RoleSpecFile] = {}
    for role in REQUIRED_ROLES:
        path = config_dir / "roles" / f"{role.value}.json"
        try:
            spec = RoleSpecFile.model_validate_json(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, ValidationError) as exc:
            raise ConfigError(f"role spec {path.name}: {exc}") from exc
        if spec.role != role:
            raise ConfigError(f"role spec {path.name} declares role {spec.role.value}")
        specs[role] = spec
    return specs
