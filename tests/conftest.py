from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

import nonebot
import pytest
from nonebot.adapters.onebot.v11 import Adapter as ONEBOT_V11Adapter
from pytest_asyncio import is_async_test

# 将项目根目录加入 sys.path，使测试可以导入 src 模块
sys.path.insert(0, str(Path(__file__).parent))

if TYPE_CHECKING:
    from collections.abc import Generator

    from _pytest.mark.structures import MarkDecorator
    from nonebot.internal.driver.abstract import Driver
    from pytest_asyncio.plugin import PytestAsyncioFunction


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    pytest_asyncio_tests: Generator[PytestAsyncioFunction] = (
        item for item in items if is_async_test(item)
    )
    session_scope_marker: MarkDecorator = pytest.mark.asyncio(loop_scope="session")
    for async_test in pytest_asyncio_tests:
        async_test.add_marker(marker=session_scope_marker, append=False)


@pytest.fixture(scope="session", autouse=True)
async def after_nonebot_init() -> None:
    init_config: dict[str, str] = {
        "LOCALSTORE_USE_CWD": "True",
        "DRIVER": "~fastapi+~httpx+~websockets",
    }
    nonebot.init(**init_config)

    # 注册适配器
    driver: Driver = nonebot.get_driver()
    driver.register_adapter(adapter=ONEBOT_V11Adapter)

    # 加载插件配置
    nonebot.load_from_toml(file_path="pyproject.toml")
    nonebot.load_plugins("src/builtin_plugins")
