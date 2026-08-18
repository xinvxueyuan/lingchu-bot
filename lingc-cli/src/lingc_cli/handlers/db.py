"""Database migration dispatch for Lingc CLI (lc db).

Wraps the installed nonebot-plugin-orm command-line so the launcher can drive
Alembic migrations (upgrade / check / revision / sync) with normalized exit
codes. The orm module is imported lazily so an unconfigured environment can
be reported cleanly as EnvironmentNotReadyError. NoneBot must be initialized
first (the orm entry point requires an initialized driver), mirroring
docker/smoke-test.py::_init_nonebot.
"""

from __future__ import annotations

import importlib
import os

from lingc_cli.exceptions import EnvironmentNotReadyError
from lingc_cli.i18n import _

# nonebot / adapters / the lingchu plugin are optional runtime deps of this
# launcher command (only ``lc db`` imports them at all).
# pyright: reportMissingImports=false


def _ensure_nonebot() -> None:
    """Initialize NoneBot once so the orm migration module can load.

    nonebot-plugin-orm requires an initialized NoneBot driver before its entry
    point runs; this mirrors the init in docker/smoke-test.py so migrations
    work both in CI (where SQLALCHEMY_DATABASE_URL is injected) and locally.
    """
    import nonebot

    try:
        nonebot.get_driver()
    except ValueError:
        pass
    else:
        return

    init_config: dict[str, object] = {
        "LOCALSTORE_USE_CWD": "True",
        "DRIVER": "~fastapi+~httpx+~websockets",
        "lingchu_adapter": "~onebot.v11",
        "LINGCHU_SUPERUSERS": {"smoke_user": {"qq": "42"}},
        "lingchu_locale": "zh_CN",
    }
    sqlalchemy_url = os.environ.get("SQLALCHEMY_DATABASE_URL")
    if sqlalchemy_url:
        init_config["SQLALCHEMY_DATABASE_URL"] = sqlalchemy_url
    nonebot.init(**init_config)

    driver = nonebot.get_driver()
    from nonebot.adapters.onebot.v11 import Adapter as OneBotV11Adapter

    driver.register_adapter(OneBotV11Adapter)
    nonebot.load_from_toml("pyproject.toml")
    nonebot.load_plugin("nonebot_plugin_lingchu_bot")


def _exit_code(result: object) -> int:
    """Normalize a click standalone-mode return value to an exit code."""
    if isinstance(result, int):
        return result
    return 0


def _error_exit_code(error: BaseException) -> int:
    """Normalize a raised click exception to a process exit code."""
    exit_code = getattr(error, "exit_code", None)
    if isinstance(exit_code, int):
        return exit_code
    return 1


def run_db(args: list[str]) -> int:
    """Run an orm subcommand and return its normalized exit code.

    Args:
        args: The orm subcommand and its arguments, e.g. ["upgrade"].

    Returns:
        The process exit code (0 on success).

    Raises:
        EnvironmentNotReadyError: If NoneBot / nonebot-plugin-orm is not installed.
    """
    try:
        _ensure_nonebot()
        orm_main = importlib.import_module("nonebot_plugin_orm.__main__")
    except ImportError as exc:
        raise EnvironmentNotReadyError(
            _("nonebot-plugin-orm is not installed; cannot run database commands.")
        ) from exc

    try:
        result = orm_main.main(args, prog_name="lc db", standalone_mode=False)
    except Exception as exc:
        return _error_exit_code(exc)
    return _exit_code(result)


__all__ = ["run_db"]
