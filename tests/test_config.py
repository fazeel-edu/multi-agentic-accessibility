import json
import shutil
from pathlib import Path

import pytest

from contract.enums import Phase
from contract.errors import ConfigError
from store import config as store_config

REAL = Path(__file__).resolve().parent.parent / "config"


@pytest.fixture
def cfg_dir(tmp_path):
    dest = tmp_path / "config"
    shutil.copytree(REAL, dest, ignore=shutil.ignore_patterns("__pycache__", "__init__.py"))
    return dest


def test_loads_real_config():
    loaded = store_config.load()
    cfg = loaded.config
    assert len(loaded.config_hash) == 64
    assert cfg.settings.thinking == "adaptive"
    assert cfg.model_for(Phase.DEV).model_id == "claude-haiku-5-5"
    assert cfg.model_for(Phase.EVAL).model_id == "claude-sonnet-5-5"
    assert cfg.settings.max_turns > 0 and cfg.settings.max_budget_usd > 0
    assert len(cfg.matrix.criteria) == 21
    assert {"1.1.1", "2.4.11"} <= {c.criterion for c in cfg.matrix.criteria}


def test_hash_is_stable(cfg_dir):
    assert store_config.load(cfg_dir).config_hash == store_config.load(cfg_dir).config_hash
    assert store_config.load(cfg_dir).config_hash == store_config.load().config_hash


@pytest.mark.parametrize("name", ["settings.toml", "criteria_matrix.json"])
def test_changing_any_file_changes_hash(cfg_dir, name):
    before = store_config.load(cfg_dir).config_hash
    with (cfg_dir / name).open("a") as f:
        f.write("\n" if name.endswith("toml") else " \n")
    assert store_config.load(cfg_dir).config_hash != before


def test_extra_and_renamed_files_change_hash(cfg_dir):
    before = store_config.load(cfg_dir).config_hash
    (cfg_dir / "role_specs").mkdir()
    (cfg_dir / "role_specs" / "keyboard.md").write_text("prompt")
    added = store_config.load(cfg_dir).config_hash
    assert added != before
    (cfg_dir / "role_specs" / "keyboard.md").rename(cfg_dir / "role_specs" / "kb.md")
    assert store_config.load(cfg_dir).config_hash != added


def test_noise_files_do_not_change_hash(cfg_dir):
    before = store_config.load(cfg_dir).config_hash
    (cfg_dir / ".DS_Store").write_text("x")
    (cfg_dir / "__pycache__").mkdir()
    (cfg_dir / "__pycache__" / "a.pyc").write_text("x")
    assert store_config.load(cfg_dir).config_hash == before


@pytest.mark.parametrize("key", ["temperature", "top_p", "max_tokens"])
def test_unpinnable_sampling_settings_are_rejected(cfg_dir, key):
    path = cfg_dir / "settings.toml"
    path.write_text(f"{key} = 0.0\n" + path.read_text())
    with pytest.raises(ConfigError):
        store_config.load(cfg_dir)


def test_missing_file_and_bad_values_raise_config_error(cfg_dir):
    (cfg_dir / "settings.toml").write_text(
        (cfg_dir / "settings.toml").read_text().replace('"adaptive"', '"manual"')
    )
    with pytest.raises(ConfigError):
        store_config.load(cfg_dir)
    (cfg_dir / "criteria_matrix.json").unlink()
    with pytest.raises(ConfigError):
        store_config.load(cfg_dir)


def test_duplicate_criterion_rejected(cfg_dir):
    import json

    p = cfg_dir / "criteria_matrix.json"
    data = json.loads(p.read_text())
    data["criteria"].append(data["criteria"][0])
    p.write_text(json.dumps(data))
    with pytest.raises(ConfigError):
        store_config.load(cfg_dir)


def test_frozen_matrix_needs_a_date_and_draft_must_not_have_one(cfg_dir):
    p = cfg_dir / "criteria_matrix.json"
    data = json.loads(p.read_text())
    for status, frozen_on in (("frozen", None), ("draft", "2026-12-01")):
        p.write_text(json.dumps({**data, "status": status, "frozen_on": frozen_on}))
        with pytest.raises(ConfigError):
            store_config.load(cfg_dir)
    p.write_text(json.dumps({**data, "status": "frozen", "frozen_on": "2026-12-01"}))
    assert store_config.load(cfg_dir).config.matrix.status == "frozen"


def test_cost_cap_must_cover_one_session_and_be_finite(cfg_dir):
    path = cfg_dir / "settings.toml"
    text = path.read_text()
    path.write_text(text.replace("cost_cap_usd = 50.0", "cost_cap_usd = 0.5"))
    with pytest.raises(ConfigError):
        store_config.load(cfg_dir)
    path.write_text(text.replace("cost_cap_usd = 50.0", "cost_cap_usd = inf"))
    with pytest.raises(ConfigError):
        store_config.load(cfg_dir)


def test_invalid_utf8_is_a_config_error(cfg_dir):
    (cfg_dir / "settings.toml").write_bytes(b"\xff\xfe\x00bad")
    with pytest.raises(ConfigError):
        store_config.load(cfg_dir)


def test_only_the_top_level_package_marker_is_ignored_by_the_hash(cfg_dir):
    before = store_config.load(cfg_dir).config_hash
    (cfg_dir / "__init__.py").write_text("")
    assert store_config.load(cfg_dir).config_hash == before
    (cfg_dir / "role_specs").mkdir()
    (cfg_dir / "role_specs" / "__init__.py").write_text("")
    assert store_config.load(cfg_dir).config_hash != before


def test_every_role_agent_has_criteria_in_the_matrix():
    from contract.enums import Role

    covered = {r for c in store_config.load().config.matrix.criteria for r in c.roles}
    agents = set(Role) - {Role.INCLUSIVE_DESIGN, Role.AXE_CORE}  # synthesis and axe have none
    assert agents <= covered
    assert "1.4.10" not in {c.criterion for c in store_config.load().config.matrix.criteria}
