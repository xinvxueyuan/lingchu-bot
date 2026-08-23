"""Tests for lingc_cli.handlers.db.run_db."""

from __future__ import annotations

import importlib
import sys
import types
from typing import TYPE_CHECKING, Any, cast

import pytest

from lingc_cli.exceptions import EnvironmentNotReadyError
from lingc_cli.handlers.db import run_db

if TYPE_CHECKING:
    from collections.abc import Callable


class _OrmUsageError(Exception):
    """Fake click usage error that carries an exit code."""

    exit_code = 2


class _OrmAbortError(Exception):
    """Fake click abort that carries no exit code."""


def _install_fake_orm(
    monkeypatch: pytest.MonkeyPatch, main: Callable[..., object]
) -> None:
    """Register a fake nonebot_plugin_orm module in sys.modules."""
    parent = types.ModuleType("nonebot_plugin_orm")
    # ``types.ModuleType`` blocks unknown attribute assignment in strict mode;
    # cast to ``Any`` so the fake ``main`` entry point can be attached.
    main_module = cast("Any", types.ModuleType("nonebot_plugin_orm.__main__"))
    main_module.main = main
    monkeypatch.setitem(sys.modules, "nonebot_plugin_orm", parent)
    monkeypatch.setitem(sys.modules, "nonebot_plugin_orm.__main__", main_module)


def test_db_not_installed_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """When orm is absent, run_db reports an unready environment."""
    monkeypatch.setattr(
        importlib,
        "import_module",
        lambda name: (_ for _ in ()).throw(ImportError(f"no {name}")),
    )
    with pytest.raises(EnvironmentNotReadyError):
        run_db(["upgrade"])


def test_db_upgrade_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """A successful main call returns 0 and receives the expected args."""
    recorded: list[tuple[object, object]] = []

    def main(*args: object, **kwargs: object) -> None:
        recorded.append((args, kwargs))

    _install_fake_orm(monkeypatch, main)
    assert run_db(["upgrade"]) == 0
    assert recorded == [
        ((["upgrade"],), {"prog_name": "lc db", "standalone_mode": False})
    ]


def test_db_returns_exit_code(monkeypatch: pytest.MonkeyPatch) -> None:
    exit_code = 3

    def main(*_args: object, **_kwargs: object) -> object:
        return exit_code

    _install_fake_orm(monkeypatch, main)
    assert run_db(["check"]) == exit_code


def test_db_raises_error_with_exit_code(monkeypatch: pytest.MonkeyPatch) -> None:
    """Click error objects carrying an exit_code are normalized to that code."""

    def main(*_args: object, **_kwargs: object) -> object:
        error = _OrmUsageError()
        raise error

    _install_fake_orm(monkeypatch, main)
    assert run_db(["revision"]) == _OrmUsageError.exit_code


def test_db_raises_abort_defaults_to_one(monkeypatch: pytest.MonkeyPatch) -> None:
    """Errors without an exit_code normalize to a generic failure code."""

    def main(*_args: object, **_kwargs: object) -> object:
        error = _OrmAbortError()
        raise error

    _install_fake_orm(monkeypatch, main)
    assert run_db(["sync"]) == 1
