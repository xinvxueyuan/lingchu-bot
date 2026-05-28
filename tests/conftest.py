"""pytest配置与NoneBot初始化。

此模块负责配置pytest测试框架与NoneBot异步驱动程序。
主要功能包括：
- pytest_configure: 在测试收集前初始化NoneBot实例和适配器
- pytest_unconfigure: 清理资源防止测试间污染
- pytest_collection_modifyitems: 统一配置异步测试的事件循环作用域

"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import nonebot
import pytest
from nonebot.adapters.milky import Adapter as MilkyAdapterilkyBot
from nonebot.adapters.onebot.v11 import Adapter as ONEBOT_V11Adapter
from pytest_asyncio import is_async_test

sys.path.insert(0, str(object=Path(__file__).parent))

# ========== 环境自动检测 ==========
if Path(".env.dev").exists():
    os.environ["ENVIRONMENT"] = "dev"
else:
    os.environ["ENVIRONMENT"] = "test"
# =================================

if TYPE_CHECKING:
    from collections.abc import Generator

    from _pytest.mark.structures import MarkDecorator
    from nonebot.drivers import Driver
    from pytest_asyncio.plugin import PytestAsyncioFunction


def pytest_configure(config: pytest.Config) -> None:
    """在收集测试之前初始化NoneBot驱动。

    此钩子函数在pytest收集测试前执行，负责初始化NoneBot框架。
    若驱动已存在则跳过，避免重复初始化。初始化后注册OneBot v11适配器，
    并从配置文件加载内置插件。

    Args:
        config: pytest的配置对象。

    """
    try:
        nonebot.get_driver()
    except ValueError:
        pass
    else:
        return

    _ = config
    init_config: dict[str, str] = {
        "LOCALSTORE_USE_CWD": "True",
        "DRIVER": "~fastapi+~httpx+~websockets",
    }
    nonebot.init(**init_config)

    driver: Driver = nonebot.get_driver()
    driver.register_adapter(adapter=ONEBOT_V11Adapter)
    driver.register_adapter(adapter=MilkyAdapterilkyBot)

    nonebot.load_from_toml(file_path="pyproject.toml")


def pytest_unconfigure(config: pytest.Config) -> None:
    """清理NoneBot驱动状态。

    此钩子函数在所有测试执行完毕后调用，负责清理全局驱动状态。
    防止残留的NoneBot驱动实例对后续测试或其他进程造成干扰。

    Args:
        config: pytest的配置对象。

    """
    _ = config
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
