"""Config loader and Config hash (AD-7, FR31). The only reader of `config/`."""

import hashlib
import json
import tomllib
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from contract.enums import Phase
from contract.errors import ConfigError
from contract.matrix import CriteriaMatrix
from store.paths import CONFIG_DIR

Effort = Literal["low", "medium", "high", "xhigh", "max"]

# Noise, not configuration: the package marker at the top level, OS files, bytecode.
_IGNORED_TOP_LEVEL = {"__init__.py"}
_IGNORED_NAMES = {".DS_Store"}
_IGNORED_DIRS = {"__pycache__"}


class _Frozen(BaseModel):
    # extra="forbid": temperature, top_p, max_tokens (and any typo) are rejected.
    model_config = ConfigDict(frozen=True, extra="forbid")


class ModelSettings(_Frozen):
    model_id: str = Field(min_length=1)
    effort: Effort


class Models(_Frozen):
    dev: ModelSettings
    eval: ModelSettings


class Settings(_Frozen):
    schema_version: Literal["1"]
    thinking: Literal["adaptive"]
    max_turns: int = Field(gt=0)
    max_budget_usd: float = Field(gt=0, allow_inf_nan=False)  # per session
    cost_cap_usd: float = Field(gt=0, allow_inf_nan=False)  # whole Run
    models: Models

    @model_validator(mode="after")
    def _cap_covers_a_session(self):
        if self.cost_cap_usd < self.max_budget_usd:
            raise ValueError("cost_cap_usd must be at least max_budget_usd")
        return self


class Config(_Frozen):
    settings: Settings
    matrix: CriteriaMatrix

    def model_for(self, phase: Phase) -> ModelSettings:
        return self.settings.models.dev if phase is Phase.DEV else self.settings.models.eval


class LoadedConfig(_Frozen):
    config: Config
    config_hash: str


def _hashed_files(config_dir: Path) -> list[Path]:
    return sorted(
        p
        for p in config_dir.rglob("*")
        if p.is_file()
        and p.name not in _IGNORED_NAMES
        and p.relative_to(config_dir).parts not in {(n,) for n in _IGNORED_TOP_LEVEL}
        and not _IGNORED_DIRS & set(p.relative_to(config_dir).parts)
    )


def config_hash(config_dir: Path = CONFIG_DIR) -> str:
    """SHA-256 over every file in the folder: relative path and bytes, in sorted order."""
    digest = hashlib.sha256()
    for path in _hashed_files(config_dir):
        digest.update(path.relative_to(config_dir).as_posix().encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def load(config_dir: Path = CONFIG_DIR) -> LoadedConfig:
    """Return the validated Config and the hash of the whole folder."""
    try:
        settings = Settings.model_validate(
            tomllib.loads((config_dir / "settings.toml").read_text(encoding="utf-8"))
        )
        matrix = CriteriaMatrix.model_validate(
            json.loads((config_dir / "criteria_matrix.json").read_text(encoding="utf-8"))
        )
    except (
        OSError,
        UnicodeDecodeError,
        tomllib.TOMLDecodeError,
        json.JSONDecodeError,
        ValidationError,
    ) as exc:
        raise ConfigError(f"invalid config in {config_dir}: {exc}") from exc
    ids = [c.criterion for c in matrix.criteria]
    if len(ids) != len(set(ids)):
        raise ConfigError("criteria_matrix.json lists a criterion twice")
    try:
        digest = config_hash(config_dir)
    except OSError as exc:
        raise ConfigError(f"cannot hash config in {config_dir}: {exc}") from exc
    return LoadedConfig(config=Config(settings=settings, matrix=matrix), config_hash=digest)
