import nonebot
import pytest
from nonebot.adapters.onebot.v11 import Adapter as ONEBOT_V11Adapter
from pytest_asyncio import is_async_test


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    pytest_asyncio_tests = (item for item in items if is_async_test(item))
    session_scope_marker = pytest.mark.asyncio(loop_scope="session")
    for async_test in pytest_asyncio_tests:
        async_test.add_marker(session_scope_marker, append=False)


@pytest.fixture(scope="session", autouse=True)
async def after_nonebot_init() -> None:
    init_config = {
        "LOCALSTORE_USE_CWD": "True",
        "DRIVER": "~fastapi+~httpx+~websockets",
    }
    nonebot.init(**init_config)

    # 注册适配器
    driver = nonebot.get_driver()
    driver.register_adapter(ONEBOT_V11Adapter)

    # 加载插件配置
    nonebot.load_from_toml("pyproject.toml")
    nonebot.load_plugins("src/builtin_plugins")
