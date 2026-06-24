from nonebot import get_adapters, get_driver, logger
from nonebot.adapters import Bot
from nonebot.internal.driver.abstract import Driver

from ..core.async_utils import fire_and_forget
from ..core.bot_state import load_bot_state
from ..core.runtime_config import ensure_runtime_config_file_async
from ..core.schemas import install_schemas
from ..handle.menu import import_handle as menu_import_handle
from ..handle.qq.adapters import import_handle as group_import_handle
from ..i18n import _async as _
from ..i18n import warm_translation_cache
from ..permissions import validate_and_seed_permission_system
from ..platforms import (
    resolve_enabled_adapters,
    resolve_registered_adapters,
    validate_enabled_adapters_loaded,
)
from ..repositories.registry import seed_registry_tables
from ..services.message_store import (
    initialize_message_store,
    record_bot_lifecycle,
    shutdown_message_store,
)


async def startup() -> None:
    """
    在应用启动时预热翻译缓存并注册命令处理器。

    依次执行：预热翻译缓存、导入并注册 group 命令处理器（含所有子模块）。
    """
    try:
        install_schemas()
    except Exception:  # noqa: BLE001
        # Schema files are editor hints; missing them does not prevent startup.
        logger.exception("Failed to install JSON5 schemas")
    await ensure_runtime_config_file_async()
    load_bot_state()
    registered_adapter_names = tuple(
        str(adapter_name) for adapter_name in get_adapters()
    )
    validate_enabled_adapters_loaded(registered_adapter_names)
    enabled_adapters = resolve_enabled_adapters()
    registered_adapters = resolve_registered_adapters(registered_adapter_names)
    ignored_adapters = registered_adapters - enabled_adapters
    logger.info(
        (await _("Lingchu 启用适配器: {adapters}")).format(
            adapters=sorted(enabled_adapters)
        )
    )
    if ignored_adapters:
        logger.debug(
            (await _("Lingchu 忽略未选中的已注册适配器: {adapters}")).format(
                adapters=sorted(ignored_adapters)
            )
        )
    await warm_translation_cache()
    await seed_registry_tables()
    await validate_and_seed_permission_system()
    await group_import_handle()
    await menu_import_handle()
    await initialize_message_store()


driver: Driver = get_driver()


@driver.on_startup
async def initialize_runtime_services() -> None:
    await startup()


@driver.on_shutdown
async def shutdown_runtime_services() -> None:
    await shutdown_message_store()


@driver.on_bot_connect
async def record_bot_connected(bot: Bot) -> None:
    fire_and_forget(
        record_bot_lifecycle(bot, "bot_connected"), name="record_bot_lifecycle"
    )


@driver.on_bot_disconnect
async def record_bot_disconnected(bot: Bot) -> None:
    fire_and_forget(
        record_bot_lifecycle(bot, "bot_disconnected"), name="record_bot_lifecycle"
    )
