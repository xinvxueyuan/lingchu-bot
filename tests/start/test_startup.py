from unittest.mock import AsyncMock, MagicMock

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.hooks.handlers import (
    lifecycle as lifecycle_module,
)
from src.plugins.nonebot_plugin_lingchu_bot.start import startup as startup_module


def _empty_registered_adapters(_names: object) -> set[str]:
    return set()


@pytest.mark.asyncio
async def test_startup_imports_group_and_menu_handlers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    group_import = AsyncMock()
    menu_import = AsyncMock(side_effect=lambda: calls.append("menu_import"))

    monkeypatch.setattr(startup_module, "install_schemas", AsyncMock())
    monkeypatch.setattr(startup_module, "ensure_runtime_config_file_async", AsyncMock())
    monkeypatch.setattr(
        startup_module,
        "ensure_menu_config_file_async",
        AsyncMock(side_effect=lambda: calls.append("ensure_menu_config")),
    )
    monkeypatch.setattr(startup_module, "load_bot_state", AsyncMock())
    monkeypatch.setattr(
        startup_module,
        "load_menu_config",
        AsyncMock(
            side_effect=lambda: (
                startup_module.menu_module.MENU_PAGES,
                startup_module.menu_module.MENU_FEATURES,
            )
        ),
    )
    monkeypatch.setattr(
        startup_module.menu_module,
        "set_menu_pages",
        MagicMock(side_effect=lambda _pages: calls.append("set_menu_pages")),
    )
    monkeypatch.setattr(
        startup_module.menu_module,
        "set_menu_features",
        MagicMock(side_effect=lambda _features: calls.append("set_menu_features")),
    )
    monkeypatch.setattr(startup_module, "get_adapters", dict)
    monkeypatch.setattr(
        startup_module,
        "validate_enabled_adapters_loaded",
        MagicMock(),
    )
    monkeypatch.setattr(
        startup_module,
        "resolve_enabled_adapters",
        lambda: {"~onebot.v11"},
    )
    monkeypatch.setattr(
        startup_module,
        "resolve_registered_adapters",
        _empty_registered_adapters,
    )
    monkeypatch.setattr(startup_module, "warm_translation_cache", AsyncMock())
    monkeypatch.setattr(startup_module, "group_import_handle", group_import)
    monkeypatch.setattr(startup_module, "menu_import_handle", menu_import)
    monkeypatch.setattr(
        startup_module,
        "validate_and_seed_permission_system",
        AsyncMock(),
    )
    monkeypatch.setattr(startup_module, "initialize_message_store", AsyncMock())
    monkeypatch.setattr(startup_module, "cleanup_expired_messages", AsyncMock())
    register_scheduler_handler = MagicMock()
    monkeypatch.setattr(
        startup_module,
        "register_scheduler_handler",
        register_scheduler_handler,
    )
    initialize_scheduler_service = AsyncMock()
    monkeypatch.setattr(
        startup_module,
        "initialize_scheduler_service",
        initialize_scheduler_service,
    )
    monkeypatch.setattr(startup_module, "seed_registry_tables", AsyncMock())

    await startup_module.startup()

    group_import.assert_awaited_once()
    menu_import.assert_awaited_once()
    register_scheduler_handler.assert_called_once_with(
        startup_module.SCHEDULER_CLEANUP_HANDLER_KEY,
        startup_module.cleanup_expired_messages,
    )
    initialize_scheduler_service.assert_awaited_once()
    assert calls.index("ensure_menu_config") < calls.index("menu_import")
    assert calls.index("set_menu_pages") < calls.index("menu_import")
    assert calls.index("set_menu_features") < calls.index("menu_import")


@pytest.mark.asyncio
async def test_lifecycle_on_startup_calls_startup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    startup = AsyncMock()
    monkeypatch.setattr(lifecycle_module, "startup", startup)

    await lifecycle_module.on_startup()

    startup.assert_awaited_once()


@pytest.mark.asyncio
async def test_lifecycle_on_shutdown_calls_scheduler_and_message_store_in_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    call_order: list[str] = []

    async def _shutdown_scheduler_service() -> None:
        call_order.append("scheduler")

    async def _shutdown_message_store() -> None:
        call_order.append("message_store")

    monkeypatch.setattr(
        lifecycle_module, "shutdown_scheduler_service", _shutdown_scheduler_service
    )
    monkeypatch.setattr(
        lifecycle_module, "shutdown_message_store", _shutdown_message_store
    )

    await lifecycle_module.on_shutdown()

    assert call_order == ["scheduler", "message_store"]


@pytest.mark.asyncio
async def test_check_announcement_image_path_bridge_emits_warning_on_mismatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Startup self-check warns when LINGCHU_ANNOUNCEMENT_IMAGE_CACHE_DIR uses a
    Windows-style drive letter on a Linux / WSL2 host."""
    from unittest.mock import patch

    fake_config = MagicMock()
    fake_config.announcement_image_cache_dir = MagicMock()
    fake_config.announcement_image_cache_dir.__str__ = lambda _: (
        "C:/dev/lingchu-bot/.local/napcat-announcement-images"
    )
    fake_config.announcement_image_protocol_dir = (
        "/lingchu-bot/.local/napcat-announcement-images"
    )
    fake_config.system_type = "Linux"

    monkeypatch.setattr(startup_module, "plugin_config", fake_config)

    with patch.object(startup_module.logger, "warning") as mock_warning:
        await startup_module._check_announcement_image_path_bridge()

    mock_warning.assert_called_once()
    message = mock_warning.call_args.args[0]
    assert "C:/dev/lingchu-bot/.local/napcat-announcement-images" in message
    assert "LINGCHU_ANNOUNCEMENT_IMAGE_CACHE_DIR" in message


@pytest.mark.asyncio
async def test_check_announcement_image_path_bridge_silent_when_consistent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Startup self-check stays silent when paths match the host platform."""
    from pathlib import Path
    from unittest.mock import patch

    fake_config = MagicMock()
    fake_config.announcement_image_cache_dir = Path(
        "/home/xinvdev/lingchu-bot/.local/napcat-announcement-images"
    )
    fake_config.announcement_image_protocol_dir = (
        "/lingchu-bot/.local/napcat-announcement-images"
    )
    fake_config.system_type = "Linux"

    monkeypatch.setattr(startup_module, "plugin_config", fake_config)

    with patch.object(startup_module.logger, "warning") as mock_warning:
        await startup_module._check_announcement_image_path_bridge()

    mock_warning.assert_not_called()
