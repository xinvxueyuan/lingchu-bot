"""Tests for lingc_cli.handlers.init and the lc init command."""

from __future__ import annotations

from typing import TYPE_CHECKING

import typer
from typer.testing import CliRunner

from lingc_cli.commands.init import register as register_init
from lingc_cli.core import config
from lingc_cli.handlers.init import MINIMAL_ENV, init_project

if TYPE_CHECKING:
    from pathlib import Path


runner = CliRunner()


def test_init_creates_missing_env(tmp_path: Path) -> None:
    created = init_project(tmp_path)
    env_file = tmp_path / ".env"
    assert created == [env_file]
    assert env_file.is_file()
    assert "NICKNAME=lingchu" in env_file.read_text(encoding="utf-8")


def test_init_does_not_overwrite_existing(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("CUSTOM=1\n", encoding="utf-8")
    created = init_project(tmp_path)
    assert created == []
    assert env_file.read_text(encoding="utf-8") == "CUSTOM=1\n"


def test_init_force_overwrites(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("CUSTOM=1\n", encoding="utf-8")
    created = init_project(tmp_path, force=True)
    assert created == [env_file]
    assert env_file.read_text(encoding="utf-8") == MINIMAL_ENV


def test_init_command_creates_env(tmp_path: Path) -> None:
    config.set_cwd(str(tmp_path))
    app = typer.Typer()
    register_init(app)
    result = runner.invoke(app, [])
    assert result.exit_code == 0
    assert "generated" in result.stdout
    env_file = tmp_path / ".env"
    assert env_file.is_file()
    assert "NICKNAME=lingchu" in env_file.read_text(encoding="utf-8")


def test_init_command_no_overwrite_without_force(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("CUSTOM=1\n", encoding="utf-8")
    config.set_cwd(str(tmp_path))
    app = typer.Typer()
    register_init(app)
    result = runner.invoke(app, [])
    assert result.exit_code == 0
    assert "already exists" in result.stdout
    assert env_file.read_text(encoding="utf-8") == "CUSTOM=1\n"
