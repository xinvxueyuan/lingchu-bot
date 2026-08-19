from nonebot import get_adapters, logger, require

require("nonebot_plugin_orm")
from nonebot_plugin_orm import get_session

from ..core.runtime_config import load_runtime_configs_on_startup
from ..handle.qq.adapters import import_handle
from ..i18n import _async as _, warm_translation_cache
from ..permissions import validate_and_seed_permission_system
from ..platforms import (
    resolve_enabled_adapters,
    resolve_registered_adapters,
    validate_enabled_adapters_loaded,
)
from ..repositories.registry import seed_registry_tables
from ..services.message_store import (
    SCHEDULER_CLEANUP_HANDLER_KEY,
    cleanup_expired_messages,
    initialize_message_store,
)
from ..services.scheduler import (
    initialize_scheduler_service,
    register_scheduler_handler,
)


async def startup() -> None:
    """Load runtime state and initialize handlers, stores, and scheduler."""
    await load_runtime_configs_on_startup()
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
    async with get_session() as session, session.begin():
        await seed_registry_tables(session)
        await validate_and_seed_permission_system(session)
    await import_handle("command")
    await import_handle("menu")
    await initialize_message_store()
    register_scheduler_handler(
        SCHEDULER_CLEANUP_HANDLER_KEY,
        cleanup_expired_messages,
    )
    await initialize_scheduler_service()
