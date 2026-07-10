"""Tests for pytest session configuration helpers."""

from __future__ import annotations

from types import SimpleNamespace

from tests.conftest import (
    _remove_orm_startup_schema_management,
    _should_skip_orm_startup_schema_management,
)


def test_orm_startup_schema_management_runs_for_local_database() -> None:
    assert _should_skip_orm_startup_schema_management(None, "master") is False


def test_orm_startup_schema_management_runs_for_serial_external_database() -> None:
    assert (
        _should_skip_orm_startup_schema_management(
            "sqlite+aiosqlite:///test.db",
            "master",
        )
        is False
    )


def test_orm_startup_schema_management_skipped_for_xdist_external_database() -> None:
    assert (
        _should_skip_orm_startup_schema_management(
            "postgresql+psycopg://test",
            "gw0",
        )
        is True
    )


def test_remove_orm_startup_schema_management_removes_only_orm_hook() -> None:
    def unrelated_startup() -> None:
        pass

    def init_orm() -> None:
        pass

    init_orm.__module__ = "nonebot_plugin_orm"
    driver = SimpleNamespace(
        _lifespan=SimpleNamespace(_startup_funcs=[unrelated_startup, init_orm])
    )

    assert _remove_orm_startup_schema_management(driver) == 1
    assert driver._lifespan._startup_funcs == [unrelated_startup]
