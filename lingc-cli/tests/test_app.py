from __future__ import annotations

from typer.testing import CliRunner

from lingc_cli.app import app

runner = CliRunner()


def test_version() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "lingc cli version" in result.stdout


def test_help() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Usage" in result.stdout
