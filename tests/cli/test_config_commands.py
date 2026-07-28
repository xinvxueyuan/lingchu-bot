from __future__ import annotations

import json
from typing import TYPE_CHECKING
from unittest.mock import patch

from _lingchu_bot_cli.app import app
from _lingchu_bot_cli.config_files import _LLM_TEMPLATE
from _lingchu_bot_contracts import MutableRuntimeSettings
from rtoml import load
from typer.testing import CliRunner

from src.plugins.nonebot_plugin_lingchu_bot.services.llm import config as llm_config
from src.plugins.nonebot_plugin_lingchu_bot.services.llm.config import (
    load_llm_runtime_config,
)

if TYPE_CHECKING:
    from pathlib import Path

    from pytest import MonkeyPatch

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
    monkeypatch: MonkeyPatch,
) -> None:
    # The test environment may carry LINGCHU_AI_MODEL from .env; clear it
    # so the no-env template path is exercised deterministically.
    monkeypatch.delenv("LINGCHU_AI_MODEL", raising=False)

    config_file = tmp_path / "runtime-overrides.toml"
    llm_file = tmp_path / "llm.toml"

    first = runner.invoke(app, ["config", "init", "--path", str(config_file)])

    assert first.exit_code == 0
    assert llm_file.read_text(encoding="utf-8") == _LLM_TEMPLATE
    llm_file.write_text(
        '[pydantic-ai]\nmodel = "anthropic:claude-sonnet-4-5"\n',
        encoding="utf-8",
    )

    second = runner.invoke(
        app, ["config", "init", "--path", str(config_file), "--force"]
    )

    assert second.exit_code == 0
    assert f"exists: {llm_file}" in second.stdout
    assert (
        llm_file.read_text(encoding="utf-8")
        == '[pydantic-ai]\nmodel = "anthropic:claude-sonnet-4-5"\n'
    )


def test_config_init_seeds_llm_from_pydantic_ai_model_env(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setenv("LINGCHU_AI_MODEL", "anthropic:claude-sonnet-4-5")

    config_file = tmp_path / "runtime-overrides.toml"
    llm_file = tmp_path / "llm.toml"

    result = runner.invoke(app, ["config", "init", "--path", str(config_file)])

    assert result.exit_code == 0
    assert llm_file.exists()

    content = llm_file.read_text(encoding="utf-8")
    assert "[pydantic-ai]" in content
    assert 'model = "anthropic:claude-sonnet-4-5"' in content
    assert "timeout = 60" in content
    assert "[mcp]" in content
    assert "[observability]" in content

    # The generated file must be loadable by load_llm_runtime_config().
    with patch.object(llm_config, "get_llm_config_file", return_value=llm_file):
        config = load_llm_runtime_config()

    assert config.pydantic_ai.model == "anthropic:claude-sonnet-4-5"
    assert config.pydantic_ai.timeout == 60.0
    assert config.mcp.enabled is False
    assert config.observability.enabled is True


def test_config_init_without_pydantic_ai_model_env_writes_commented_template(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.delenv("LINGCHU_AI_MODEL", raising=False)

    config_file = tmp_path / "runtime-overrides.toml"
    llm_file = tmp_path / "llm.toml"

    result = runner.invoke(app, ["config", "init", "--path", str(config_file)])

    assert result.exit_code == 0
    content = llm_file.read_text(encoding="utf-8")
    assert content == _LLM_TEMPLATE
    assert 'model = "openai:gpt-5.2"' in content


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
