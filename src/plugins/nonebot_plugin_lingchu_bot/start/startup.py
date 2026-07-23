from nonebot import get_adapters, logger, require

require("nonebot_plugin_orm")
from nonebot_plugin_orm import get_session

from ..core.bot_state import load_bot_state
from ..core.config import (
    get_handle_config_manager,
    initialize_handle_config_manager,
)
from ..core.menu_config import ensure_menu_config_file_async, load_menu_config
from ..handle import menu as menu_module
from ..handle.menu import import_handle as menu_import_handle
from ..handle.qq.adapters import import_handle as group_import_handle
from ..i18n import _async as _, warm_translation_cache
from ..permissions import validate_and_seed_permission_system
from ..platforms import (
    resolve_enabled_adapters,
    resolve_registered_adapters,
    validate_enabled_adapters_loaded,
)
from ..repositories.registry import seed_registry_tables
from ..services.llm.config import ensure_llm_config_file_async
from ..services.llm.mcp_lifecycle import initialize_mcp_agent_runtime
from ..services.llm.runtime import initialize_llm_runtime
from ..services.message_store import (
    SCHEDULER_CLEANUP_HANDLER_KEY,
    cleanup_expired_messages,
    initialize_message_store,
)
from ..services.scheduler import (
    initialize_scheduler_service,
    register_scheduler_handler,
)


async def _initialize_ai() -> None:
    await ensure_llm_config_file_async()
    await initialize_llm_runtime()
    await initialize_mcp_agent_runtime()


async def startup() -> None:
    """Initialize configuration, optional AI, handlers, stores, and scheduler."""
    try:
        await _initialize_ai()
    except Exception:
        # AI is optional; configuration or backend-local dependency failures
        # must not prevent the bot's non-AI services from starting.
        logger.exception("Failed to initialize LLM runtime; AI is unavailable")
    try:
        await ensure_menu_config_file_async()
    except Exception:
        logger.exception("Failed to ensure menu config file")
    try:
        await get_handle_config_manager().ensure_config_files()
    except Exception:
        logger.exception("Failed to ensure handle config files")
    await load_bot_state()
    try:
        menu_pages, menu_features = await load_menu_config()
        menu_module.set_menu_pages(menu_pages)
        menu_module.set_menu_features(menu_features)
    except Exception:
        logger.exception("Failed to load menu config")
    try:
        await initialize_handle_config_manager()
    except Exception:
        logger.exception("Failed to initialize handle config manager")
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
    await group_import_handle()
    await menu_import_handle()
    await initialize_message_store()
    register_scheduler_handler(
        SCHEDULER_CLEANUP_HANDLER_KEY,
        cleanup_expired_messages,
    )
    await initialize_scheduler_service()
