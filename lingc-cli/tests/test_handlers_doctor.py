"""Tests for lingc_cli.handlers.doctor and the lc doctor command."""

from __future__ import annotations

from typing import TYPE_CHECKING

import typer
from typer.testing import CliRunner

from lingc_cli.commands.doctor import MISSING_EXIT_CODE, register as register_doctor
from lingc_cli.core import config
from lingc_cli.handlers.doctor import Check, has_missing, run_checks

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

runner = CliRunner()


class _FakeDist:
    def __init__(self, name: str, version: str) -> None:
        self.version = version
        self.metadata = {"Name": name}


def _make_distributions(*names: str) -> list[_FakeDist]:
    return [_FakeDist(name, "0.1.0") for name in names]


def _write_env(root: Path) -> None:
    env = 'NICKNAME=lingchu\nDRIVER=~fastapi\nSUPERUSERS=[]\nCOMMAND_START=["/"]'
    root.joinpath(".env").write_text(env, encoding="utf-8")


def _patch_metadata(monkeypatch: pytest.MonkeyPatch, *, core: bool) -> None:
    names = ["nonebot2", "nonebot-adapter-onebot"] if core else []
    monkeypatch.setattr(
        "importlib.metadata.distributions",
        lambda: _make_distributions(*names),
    )
    monkeypatch.setattr(
        "importlib.metadata.version",
        lambda name: "0.1.0" if (core and name == "nonebot2") else None,
    )


def _run_doctor(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, *, core: bool
) -> tuple[int, str]:
    _patch_metadata(monkeypatch, core=core)
    config.set_cwd(str(tmp_path))
    app = typer.Typer()
    register_doctor(app)
    result = runner.invoke(app, [])
    return result.exit_code, result.stdout


def test_run_checks_ok(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_metadata(monkeypatch, core=True)
    _write_env(tmp_path)
    checks = run_checks(tmp_path)
    statuses = {check.name: check.status for check in checks}
    assert statuses["core"] == "ok"
    assert statuses["adapters"] == "ok"
    assert statuses["config"] == "ok"
    assert not has_missing(checks)


def test_run_checks_missing_core(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_metadata(monkeypatch, core=False)
    _write_env(tmp_path)
    checks = run_checks(tmp_path)
    statuses = {check.name: check.status for check in checks}
    assert statuses["core"] == "missing"
    assert statuses["adapters"] == "missing"
    assert has_missing(checks)


def test_doctor_exit_zero(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_env(tmp_path)
    exit_code, _ = _run_doctor(monkeypatch, tmp_path, core=True)
    assert exit_code == 0


def test_doctor_exit_three_when_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_env(tmp_path)
    exit_code, _ = _run_doctor(monkeypatch, tmp_path, core=False)
    assert exit_code == MISSING_EXIT_CODE


def test_check_dataclass() -> None:
    check = Check(name="core", status="ok", detail="2.3.3")
    assert check.name == "core"
    assert check.status == "ok"
    assert check.detail == "2.3.3"
    assert check.advice == ""
