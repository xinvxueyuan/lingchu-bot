from importlib.metadata import PackageNotFoundError, version
import json
from unittest.mock import patch

from _lingchu_bot_cli.app import app
from typer.testing import CliRunner

runner = CliRunner()


def test_cli_help_is_available_without_nonebot_runtime() -> None:
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "Lingchu Bot operations" in result.stdout


def test_cli_reports_installed_distribution_version() -> None:
    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0
    assert result.stdout.strip() == version("nonebot-plugin-lingchu-bot")


def test_config_path_reports_all_localstore_roots() -> None:
    result = runner.invoke(app, ["config", "path"])

    assert result.exit_code == 0
    assert "config:" in result.stdout
    assert "data:" in result.stdout
    assert "cache:" in result.stdout


def test_doctor_json_is_machine_readable() -> None:
    result = runner.invoke(app, ["doctor", "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert [check["name"] for check in payload["checks"]] == [
        "nonebot2",
        "nonebot-adapter-onebot",
        "nonebot-plugin-localstore",
        "nonebot-plugin-lingchu-bot",
    ]
    assert all(check["status"] == "ok" for check in payload["checks"])


def test_doctor_reports_required_runtime_components() -> None:
    result = runner.invoke(app, ["doctor"])

    assert result.exit_code == 0
    assert "nonebot2:" in result.stdout
    assert "nonebot-adapter-onebot:" in result.stdout
    assert "nonebot-plugin-localstore:" in result.stdout
    assert "nonebot-plugin-lingchu-bot:" in result.stdout


def test_doctor_json_reports_missing_dependency_with_nonzero_exit() -> None:
    def missing_one(distribution: str) -> str:
        if distribution == "nonebot-adapter-onebot":
            raise PackageNotFoundError(distribution)
        return "1.0"

    with patch("_lingchu_bot_cli.app.version", side_effect=missing_one):
        result = runner.invoke(app, ["doctor", "--json"])

    assert result.exit_code == 2
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert next(
        check
        for check in payload["checks"]
        if check["name"] == "nonebot-adapter-onebot"
    ) == {
        "name": "nonebot-adapter-onebot",
        "status": "missing",
        "version": None,
    }
