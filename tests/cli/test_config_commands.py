from __future__ import annotations

import json
from typing import TYPE_CHECKING

from _lingchu_bot_cli.app import app
from _lingchu_bot_contracts import MutableRuntimeSettings
from rtoml import load
from typer.testing import CliRunner

if TYPE_CHECKING:
    from pathlib import Path

runner = CliRunner()


def test_config_init_creates_defaults_without_overwriting_user_file(
    tmp_path: Path,
) -> None:
    config_file = tmp_path / "runtime-overrides.toml"

    first = runner.invoke(app, ["config", "init", "--path", str(config_file)])

    assert first.exit_code == 0
    assert config_file.exists()
    assert load(config_file) == MutableRuntimeSettings().model_dump(mode="json")
    original = config_file.read_bytes()

    second = runner.invoke(app, ["config", "init", "--path", str(config_file)])

    assert second.exit_code == 0
    assert "exists" in second.stdout
    assert config_file.read_bytes() == original


def test_config_init_creates_llm_template_without_overwriting_existing_file(
    tmp_path: Path,
) -> None:
    config_file = tmp_path / "runtime-overrides.toml"
    llm_file = tmp_path / "llm.toml"

    first = runner.invoke(app, ["config", "init", "--path", str(config_file)])

    assert first.exit_code == 0
    assert llm_file.read_text(encoding="utf-8") == (
        'default_profile = "default"\n[profiles]\n'
    )
    llm_file.write_text('[profiles.keep]\nmodel = "gpt"\n', encoding="utf-8")

    second = runner.invoke(
        app, ["config", "init", "--path", str(config_file), "--force"]
    )

    assert second.exit_code == 0
    assert f"exists: {llm_file}" in second.stdout
    assert llm_file.read_text(encoding="utf-8") == '[profiles.keep]\nmodel = "gpt"\n'


def test_config_validate_is_read_only_for_valid_file(tmp_path: Path) -> None:
    config_file = tmp_path / "runtime-overrides.toml"
    assert (
        runner.invoke(app, ["config", "init", "--path", str(config_file)]).exit_code
        == 0
    )
    original = config_file.read_bytes()

    result = runner.invoke(app, ["config", "validate", "--path", str(config_file)])

    assert result.exit_code == 0
    assert "valid" in result.stdout
    assert config_file.read_bytes() == original


def test_config_validate_rejects_invalid_file_without_rewriting(tmp_path: Path) -> None:
    config_file = tmp_path / "runtime-overrides.toml"
    config_file.write_text(
        'permission_platform_runtime_passthrough = "invalid"\n', encoding="utf-8"
    )
    original = config_file.read_bytes()

    result = runner.invoke(app, ["config", "validate", "--path", str(config_file)])

    assert result.exit_code == 1
    assert "invalid" in result.stderr
    assert config_file.read_bytes() == original


def test_schema_install_writes_the_shared_runtime_settings_schema(
    tmp_path: Path,
) -> None:
    result = runner.invoke(app, ["schema", "install", "--config-dir", str(tmp_path)])

    assert result.exit_code == 0
    schema_file = tmp_path / "runtime-overrides.schema.json"
    assert json.loads(schema_file.read_text(encoding="utf-8")) == (
        MutableRuntimeSettings.model_json_schema(mode="serialization")
    )
