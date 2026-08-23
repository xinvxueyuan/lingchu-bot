"""Tests for the ``lc run`` CLI command wiring."""

from __future__ import annotations

from typing import TYPE_CHECKING

from typer.testing import CliRunner

from lingc_cli.app import app as real_app
from lingc_cli.commands import run as run_command_mod
from lingc_cli.exceptions import EnvironmentNotReadyError

if TYPE_CHECKING:
    from pathlib import Path

    from _pytest.monkeypatch import MonkeyPatch
    import typer

SUCCESS_EXIT = 2
runner = CliRunner()


def _make_app() -> typer.Typer:
    return real_app


async def fake_run_success(
    cmd: list[str],
    *,
    cwd: Path | None = None,
    timeout: int = 30,
    reload: bool = False,
) -> int:
    del cmd, cwd, timeout, reload
    return 2


async def fake_run_error(
    cmd: list[str],
    *,
    cwd: Path | None = None,
    timeout: int = 30,
    reload: bool = False,
) -> int:
    del cmd, cwd, timeout, reload
    raise EnvironmentNotReadyError


def test_run_success_passes_exit_code(
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setattr(run_command_mod, "run_handler", fake_run_success)
    result = runner.invoke(_make_app(), ["run"])
    assert result.exit_code == SUCCESS_EXIT


def test_run_error_exits_with_code_1(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(run_command_mod, "run_handler", fake_run_error)
    result = runner.invoke(_make_app(), ["run"])
    assert result.exit_code == 1
    assert "Error:" in result.stderr


def test_run_help_lists_options() -> None:
    result = runner.invoke(_make_app(), ["run", "--help"])
    assert result.exit_code == 0
    assert "--reload" in result.stdout
    assert "--timeout" in result.stdout
