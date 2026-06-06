from nonebot.adapters import Bot
from nonebot.internal.driver.abstract import Driver

from ..core.runtime_config import ensure_runtime_config_file
from ..handle.commands.group import import_handle as group_import_handle
from ..i18n import warm_translation_cache
from ..platforms import validate_platform_adapter_selection
from ..services.messagestore import (
    initialize_message_store,
    record_bot_lifecycle,
    shutdown_message_store,
)


async def startup() -> None:
    """
    在应用启动时预热翻译缓存并注册命令处理器。

    依次执行：预热翻译缓存、导入并注册 group 命令处理器（含所有子模块）。
    """
    ensure_runtime_config_file()
    validate_platform_adapter_selection(
        tuple(str(adapter_name) for adapter_name in driver._adapters)
    )
    await warm_translation_cache()
    await group_import_handle()
    await initialize_message_store()


from nonebot import get_driver

driver: Driver = get_driver()


@driver.on_startup
async def initialize_runtime_services() -> None:
    await startup()


@driver.on_shutdown
async def shutdown_runtime_services() -> None:
    await shutdown_message_store()


@driver.on_bot_connect
async def record_bot_connected(bot: Bot) -> None:
    await record_bot_lifecycle(bot, "bot_connected")


@driver.on_bot_disconnect
async def record_bot_disconnected(bot: Bot) -> None:
    await record_bot_lifecycle(bot, "bot_disconnected")
