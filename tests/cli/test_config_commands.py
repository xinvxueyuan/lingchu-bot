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


def test_config_migrate_dry_run_is_read_only_and_redacts_secrets(
    tmp_path: Path,
) -> None:
    source = tmp_path / "config.toml"
    env_file = tmp_path / ".env"
    residual = tmp_path / "runtime-overrides.toml"
    source.write_text(
        'ai_api_key = "top-secret-token"\n'
        '[command_trigger_overrides.menu]\nchinese = "帮助"\n',
        encoding="utf-8",
    )
    original = source.read_bytes()

    result = runner.invoke(
        app,
        [
            "config",
            "migrate",
            "--source",
            str(source),
            "--env-file",
            str(env_file),
            "--residual",
            str(residual),
            "--dry-run",
        ],
    )

    assert result.exit_code == 0
    assert "LINGCHU_AI_API_KEY" in result.stdout
    assert "top-secret-token" not in result.stdout
    assert "command_trigger_overrides" in result.stdout
    assert not env_file.exists()
    assert not residual.exists()
    assert source.read_bytes() == original


def test_config_migrate_splits_only_explicit_source_fields(tmp_path: Path) -> None:
    source = tmp_path / "config.toml"
    env_file = tmp_path / ".env"
    residual = tmp_path / "runtime-overrides.toml"
    source.write_text(
        "message_store_retention_days = 7\n"
        'lingchu_adapter = "~onebot.v11"\n'
        '[command_trigger_overrides.menu]\nchinese = "帮助"\n',
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        [
            "config",
            "migrate",
            "--source",
            str(source),
            "--env-file",
            str(env_file),
            "--residual",
            str(residual),
        ],
    )

    assert result.exit_code == 0
    env_text = env_file.read_text(encoding="utf-8")
    assert "LINGCHU_MESSAGE_STORE_RETENTION_DAYS=7" in env_text
    assert 'LINGCHU_ADAPTER="~onebot.v11"' in env_text
    assert "LINGCHU_AI_API_KEY" not in env_text
    assert "COMMAND_TRIGGER_OVERRIDES" not in env_text
    assert load(residual) == {
        "command_trigger_overrides": {"menu": {"chinese": "帮助"}}
    }
    assert source.exists()


def test_config_migrate_rejects_conflict_without_partial_write(tmp_path: Path) -> None:
    source = tmp_path / "config.toml"
    env_file = tmp_path / ".env"
    residual = tmp_path / "runtime-overrides.toml"
    source.write_text("message_store_retention_days = 7\n", encoding="utf-8")
    env_file.write_text(
        "# user setting\nOTHER_SETTING=kept\nLINGCHU_MESSAGE_STORE_RETENTION_DAYS=30\n",
        encoding="utf-8",
    )
    original = env_file.read_bytes()

    result = runner.invoke(
        app,
        [
            "config",
            "migrate",
            "--source",
            str(source),
            "--env-file",
            str(env_file),
            "--residual",
            str(residual),
        ],
    )

    assert result.exit_code == 1
    assert "conflict" in result.stderr.lower()
    assert env_file.read_bytes() == original
    assert not residual.exists()
    assert source.exists()


def test_config_migrate_force_preserves_other_keys_and_is_idempotent(
    tmp_path: Path,
) -> None:
    source = tmp_path / "config.toml"
    env_file = tmp_path / ".env"
    residual = tmp_path / "runtime-overrides.toml"
    source.write_text("message_store_retention_days = 7\n", encoding="utf-8")
    env_file.write_text(
        "# user setting\nOTHER_SETTING=kept\nLINGCHU_MESSAGE_STORE_RETENTION_DAYS=30\n",
        encoding="utf-8",
    )
    command = [
        "config",
        "migrate",
        "--source",
        str(source),
        "--env-file",
        str(env_file),
        "--residual",
        str(residual),
        "--force",
    ]

    first = runner.invoke(app, command)
    first_env = env_file.read_bytes()
    first_residual = residual.read_bytes()
    second = runner.invoke(app, command)

    assert first.exit_code == 0
    assert second.exit_code == 0
    assert env_file.read_text(encoding="utf-8").startswith(
        "# user setting\nOTHER_SETTING=kept\n"
    )
    assert "LINGCHU_MESSAGE_STORE_RETENTION_DAYS=7" in env_file.read_text(
        encoding="utf-8"
    )
    assert env_file.read_bytes() == first_env
    assert residual.read_bytes() == first_residual
    assert source.exists()
