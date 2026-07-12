from nonebot import get_adapters, logger

from ..core.bot_state import load_bot_state
from ..core.config import plugin_config
from ..core.menu_config import ensure_menu_config_file_async, load_menu_config
from ..core.runtime_config import (
    ensure_runtime_config_file_async,
    get_handle_config_manager,
    initialize_handle_config_manager,
)
from ..core.schemas import install_schemas
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
from ..services.message_store import (
    SCHEDULER_CLEANUP_HANDLER_KEY,
    cleanup_expired_messages,
    initialize_message_store,
)
from ..services.scheduler import (
    initialize_scheduler_service,
    register_scheduler_handler,
)


async def _check_announcement_image_path_bridge() -> None:
    """Validate announcement image path bridge configuration.

    Validates that ``ANNOUNCEMENT_IMAGE_*`` path bridge configuration matches
    the current host platform.

    Path bridge misconfiguration is the most common cause of
    ``_send_group_notice`` failing with ``retcode=1200`` when a user
    migrates between Windows and WSL2, so we surface a single WARNING at
    startup instead of waiting for the next announcement to fail.
    """
    # Late import: importing the module also registers the
    # ``send_group_announcement`` matcher via ``on_alconna``. We do not
    # want that side effect earlier than necessary, so import inside the
    # function and rely on the same registration that
    # ``group_import_handle`` triggers later.
    from ..handle.qq.commands.announcement import _detect_cache_path_style_mismatch

    mismatch = _detect_cache_path_style_mismatch(
        plugin_config.announcement_image_cache_dir,
        plugin_config.announcement_image_protocol_dir,
        plugin_config.system_type,
    )
    if mismatch is None:
        return
    template = await _(
        "公告图片缓存目录 {cache_dir} 与当前系统 {system_type} 不兼容：\n"
        "当前进程在 {system_type} 上运行，但"
        " LINGCHU_ANNOUNCEMENT_IMAGE_CACHE_DIR 的值带有"
        "另一操作系统（{detected_style}）的路径风格，会被 pathlib 解析为相对路径。\n"
        "请按目标部署环境更新 .env 中的"
        " LINGCHU_ANNOUNCEMENT_IMAGE_CACHE_DIR 与"
        " LINGCHU_ANNOUNCEMENT_IMAGE_PROTOCOL_DIR，"
        "并重建 NapCat 容器使 bind mount 生效。"
    )
    logger.warning(
        template.format(
            cache_dir=mismatch.cache_dir,
            system_type=mismatch.system_type,
            detected_style=mismatch.detected_style,
        )
    )


async def startup() -> None:
    """
    在应用启动时预热翻译缓存并注册命令处理器。

    依次执行：预热翻译缓存、导入并注册 group 命令处理器（含所有子模块）。
    """
    try:
        await install_schemas()
    except Exception:
        # Schema files are editor hints; missing them does not prevent startup.
        logger.exception("Failed to install TOML schemas")
    try:
        await _check_announcement_image_path_bridge()
    except Exception:
        # Self-check failures must never block startup; the failure case
        # is also reported later via the runtime warning on the actual
        # _send_group_notice call.
        logger.exception("Failed to run announcement image path bridge self-check")
    await ensure_runtime_config_file_async()
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
    await seed_registry_tables()
    await validate_and_seed_permission_system()
    await group_import_handle()
    await menu_import_handle()
    await initialize_message_store()
    register_scheduler_handler(
        SCHEDULER_CLEANUP_HANDLER_KEY,
        cleanup_expired_messages,
    )
    await initialize_scheduler_service()
