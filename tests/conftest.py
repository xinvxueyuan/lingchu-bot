"""pytest配置与NoneBot初始化。

此模块负责配置pytest测试框架与NoneBot异步驱动程序。
主要功能包括：
- pytest_configure: 在测试收集前初始化NoneBot实例和适配器
- pytest_unconfigure: 清理资源防止测试间污染
- pytest_collection_modifyitems: 统一配置异步测试的事件循环作用域

"""

from __future__ import annotations

import inspect
import os
from pathlib import Path
import sys
from types import MethodType
from typing import TYPE_CHECKING, Any

import nonebot
from nonebot.adapters.onebot.v11 import Adapter as ONEBOT_V11Adapter
from nonebug import NONEBOT_START_LIFESPAN
import pytest
from pytest_asyncio import is_async_test

sys.path.insert(0, str(object=Path(__file__).parent))

os.environ.setdefault("ENVIRONMENT", "test")

_WORKER_ID = os.environ.get("PYTEST_XDIST_WORKER", "master")
_LOCALSTORE_ROOT = Path(".pytest-localstore") / _WORKER_ID

if TYPE_CHECKING:
    from collections.abc import Callable, Generator

    from _pytest.mark.structures import MarkDecorator
    from nonebot.drivers import Driver
    from pytest_asyncio.plugin import PytestAsyncioFunction


def _should_serialize_startup_for_shared_database(
    sqlalchemy_url: str | None,
    worker_id: str,
) -> bool:
    """Avoid startup DB write races when xdist workers share an external database."""
    return bool(sqlalchemy_url and worker_id != "master")


def _acquire_shared_startup_lock() -> Any:
    import fcntl

    lock_path = Path(".pytest-localstore") / "shared-db-startup.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_file = lock_path.open("w", encoding="utf-8")
    fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
    return lock_file


def _release_shared_startup_lock(lock_file: Any) -> None:
    import fcntl

    try:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
    finally:
        lock_file.close()


def _serialize_startup_for_shared_database(driver: object) -> int:
    lifespan = getattr(driver, "_lifespan", None)
    startup_funcs = getattr(lifespan, "_startup_funcs", None)
    startup = getattr(lifespan, "startup", None)
    if not isinstance(startup_funcs, list) or not callable(startup):
        return 0

    if not startup_funcs:
        return 0

    original_startup: Callable[[], object] = startup

    async def locked_startup(self: object) -> None:
        _ = self
        lock_file = _acquire_shared_startup_lock()
        try:
            result = original_startup()
            if inspect.isawaitable(result):
                await result
        finally:
            _release_shared_startup_lock(lock_file)

    lifespan_obj: Any = lifespan
    lifespan_obj.startup = MethodType(locked_startup, lifespan)
    return len(startup_funcs)


def _disable_nonebug_auto_lifespan(config: pytest.Config) -> None:
    """Keep nonebug from starting the full driver lifespan for every test run."""
    config.stash[NONEBOT_START_LIFESPAN] = False


def pytest_configure(config: pytest.Config) -> None:
    """在收集测试之前初始化NoneBot驱动。

    此钩子函数在pytest收集测试前执行，负责初始化NoneBot框架。
    若驱动已存在则跳过，避免重复初始化。初始化后注册OneBot v11适配器，
    并从配置文件加载内置插件。

    Args:
        config: pytest的配置对象。

    """
    config.addinivalue_line(
        "markers", "i18n: tests that run against multiple locales (zh_CN and en_US)"
    )
    _disable_nonebug_auto_lifespan(config)

    try:
        nonebot.get_driver()
    except ValueError:
        pass
    else:
        return

    _ = config
    # Support multi-database testing via SQLALCHEMY_DATABASE_URL env var.
    sqlalchemy_url = os.environ.get("SQLALCHEMY_DATABASE_URL")
    init_config: dict[str, Any] = {
        "DRIVER": "~fastapi+~httpx+~websockets",
        "alembic_startup_check": False,
        "localstore_cache_dir": _LOCALSTORE_ROOT / "cache",
        "localstore_config_dir": _LOCALSTORE_ROOT / "config",
        "localstore_data_dir": _LOCALSTORE_ROOT / "data",
        "localstore_use_cwd": False,
        "lingchu_adapter": "~onebot.v11",
        "LINGCHU_SUPERUSERS": {"user1": {"qq": "42"}},
        "lingchu_locale": "zh_CN",
    }
    if sqlalchemy_url:
        init_config["SQLALCHEMY_DATABASE_URL"] = sqlalchemy_url
    nonebot.init(**init_config)

    driver: Driver = nonebot.get_driver()
    driver.register_adapter(adapter=ONEBOT_V11Adapter)

    nonebot.load_from_toml(file_path="pyproject.toml")

    # xdist workers share each external CI database. Serialize startup DB writes
    # so ORM schema sync and project seed logic cannot race on shared tables.
    if _should_serialize_startup_for_shared_database(sqlalchemy_url, _WORKER_ID):
        _serialize_startup_for_shared_database(driver)


def pytest_unconfigure(config: pytest.Config) -> None:
    """清理NoneBot驱动状态。

    此钩子函数在所有测试执行完毕后调用，负责清理全局驱动状态。
    防止残留的NoneBot驱动实例对后续测试或其他进程造成干扰。

    注意：在 session 作用域的异步测试中，NoneBot driver 和 SQLAlchemy
    MetaData 必须在整个 session 中保持存活，否则会导致表重复定义错误。
    因此，此函数仅在其他进程需要时才清理 driver。

    Args:
        config: pytest的配置对象。

    """
    _ = config
    # 在 session 作用域的测试中，不要清理 driver，避免 SQLAlchemy 表重复定义
    # 如果确实需要清理（例如在其他进程运行测试），可以设置环境变量 PYTEST_CLEANUP_DRIVER=1
    if os.environ.get("PYTEST_CLEANUP_DRIVER") != "1":
        return
    try:
        nonebot.get_driver()
    except ValueError:
        return
    nonebot._driver = None


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """为所有异步测试统一配置事件循环作用域。

    此钩子函数在测试收集阶段，为所有异步测试添加session作用域的
    asyncio标记，确保所有测试共享同一个事件循环，提高测试效率。

    Args:
        items: pytest收集到的所有测试项。

    """
    pytest_asyncio_tests: Generator[PytestAsyncioFunction] = (
        item for item in items if is_async_test(item)
    )
    session_scope_marker: MarkDecorator = pytest.mark.asyncio(loop_scope="session")
    for async_test in pytest_asyncio_tests:
        async_test.add_marker(marker=session_scope_marker, append=False)
