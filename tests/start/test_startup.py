from unittest.mock import AsyncMock, MagicMock

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.hooks.handlers import (
    lifecycle as lifecycle_module,
)
from src.plugins.nonebot_plugin_lingchu_bot.start import startup as startup_module


def _empty_registered_adapters(_names: object) -> set[str]:
    return set()


def _apply_default_startup_mocks(
    monkeypatch: pytest.MonkeyPatch,
) -> dict[str, MagicMock | AsyncMock]:
    """Apply the standard startup mocks used by exception-path tests.

    Returns a dict of mock objects so individual tests can assert on them.
    Each mock defaults to a successful no-op; tests override the specific
    mock they want to fail.
    """
    log_exception = MagicMock()
    monkeypatch.setattr(startup_module.logger, "exception", log_exception)

    monkeypatch.setattr(startup_module, "install_schemas", AsyncMock())
    monkeypatch.setattr(startup_module, "ensure_runtime_config_file_async", AsyncMock())
    monkeypatch.setattr(startup_module, "ensure_llm_config_file_async", AsyncMock())
    monkeypatch.setattr(startup_module, "initialize_llm_runtime", AsyncMock())
    monkeypatch.setattr(
        startup_module, "_check_announcement_image_path_bridge", AsyncMock()
    )
    monkeypatch.setattr(startup_module, "ensure_menu_config_file_async", AsyncMock())

    handle_manager_mock = MagicMock()
    handle_manager_mock.ensure_config_files = AsyncMock()
    monkeypatch.setattr(
        startup_module, "get_handle_config_manager", lambda: handle_manager_mock
    )

    monkeypatch.setattr(startup_module, "load_bot_state", AsyncMock())
    monkeypatch.setattr(
        startup_module,
        "load_menu_config",
        AsyncMock(
            return_value=(
                startup_module.menu_module.MENU_PAGES,
                startup_module.menu_module.MENU_FEATURES,
            )
        ),
    )
    monkeypatch.setattr(startup_module.menu_module, "set_menu_pages", MagicMock())
    monkeypatch.setattr(startup_module.menu_module, "set_menu_features", MagicMock())
    monkeypatch.setattr(startup_module, "initialize_handle_config_manager", AsyncMock())
    monkeypatch.setattr(startup_module, "get_adapters", dict)
    monkeypatch.setattr(startup_module, "validate_enabled_adapters_loaded", MagicMock())
    monkeypatch.setattr(
        startup_module, "resolve_enabled_adapters", lambda: {"~onebot.v11"}
    )
    monkeypatch.setattr(
        startup_module, "resolve_registered_adapters", _empty_registered_adapters
    )
    monkeypatch.setattr(startup_module, "warm_translation_cache", AsyncMock())
    monkeypatch.setattr(startup_module, "seed_registry_tables", AsyncMock())
    monkeypatch.setattr(
        startup_module, "validate_and_seed_permission_system", AsyncMock()
    )
    group_import = AsyncMock()
    menu_import = AsyncMock()
    monkeypatch.setattr(startup_module, "group_import_handle", group_import)
    monkeypatch.setattr(startup_module, "menu_import_handle", menu_import)
    monkeypatch.setattr(startup_module, "initialize_message_store", AsyncMock())
    monkeypatch.setattr(startup_module, "cleanup_expired_messages", AsyncMock())
    register_scheduler_handler = MagicMock()
    monkeypatch.setattr(
        startup_module, "register_scheduler_handler", register_scheduler_handler
    )
    initialize_scheduler_service = AsyncMock()
    monkeypatch.setattr(
        startup_module,
        "initialize_scheduler_service",
        initialize_scheduler_service,
    )

    return {
        "log_exception": log_exception,
        "handle_manager_mock": handle_manager_mock,
        "group_import": group_import,
        "menu_import": menu_import,
        "register_scheduler_handler": register_scheduler_handler,
        "initialize_scheduler_service": initialize_scheduler_service,
    }


@pytest.mark.asyncio
@pytest.mark.parametrize("llm_error", [None, ValueError("invalid LLM configuration")])
async def test_startup_imports_group_and_menu_handlers(
    monkeypatch: pytest.MonkeyPatch,
    llm_error: ValueError | None,
) -> None:
    calls: list[str] = []
    group_import = AsyncMock()
    menu_import = AsyncMock(side_effect=lambda: calls.append("menu_import"))

    monkeypatch.setattr(
        startup_module,
        "install_schemas",
        AsyncMock(side_effect=lambda: calls.append("install_schemas")),
    )
    log_exception = MagicMock()
    monkeypatch.setattr(startup_module.logger, "exception", log_exception)
    monkeypatch.setattr(
        startup_module,
        "ensure_runtime_config_file_async",
        AsyncMock(side_effect=lambda: calls.append("ensure_runtime_config")),
    )

    async def _initialize_llm_runtime() -> None:
        calls.append("initialize_llm_runtime")
        if llm_error is not None:
            raise llm_error

    monkeypatch.setattr(
        startup_module,
        "ensure_llm_config_file_async",
        AsyncMock(side_effect=lambda: calls.append("ensure_llm_config")),
        raising=False,
    )
    monkeypatch.setattr(
        startup_module,
        "initialize_llm_runtime",
        _initialize_llm_runtime,
        raising=False,
    )
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
    assert calls.index("install_schemas") < calls.index("ensure_runtime_config")
    assert calls.index("ensure_runtime_config") < calls.index("ensure_llm_config")
    assert calls.index("ensure_llm_config") < calls.index("initialize_llm_runtime")
    assert calls.index("initialize_llm_runtime") < calls.index("ensure_menu_config")
    assert calls.index("ensure_menu_config") < calls.index("menu_import")
    assert calls.index("set_menu_pages") < calls.index("menu_import")
    assert calls.index("set_menu_features") < calls.index("menu_import")
    if llm_error is not None:
        log_exception.assert_called_once_with(
            "Failed to initialize LLM runtime; AI is unavailable"
        )


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

    async def _shutdown_llm_runtime() -> None:
        call_order.append("llm")

    monkeypatch.setattr(
        lifecycle_module, "shutdown_scheduler_service", _shutdown_scheduler_service
    )
    monkeypatch.setattr(
        lifecycle_module,
        "shutdown_llm_runtime",
        _shutdown_llm_runtime,
        raising=False,
    )
    monkeypatch.setattr(
        lifecycle_module, "shutdown_message_store", _shutdown_message_store
    )

    await lifecycle_module.on_shutdown()

    assert call_order == ["scheduler", "llm", "message_store"]


@pytest.mark.asyncio
async def test_check_announcement_image_path_bridge_emits_warning_on_mismatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Startup self-check warns on cache path style mismatch.

    Verifies that ``LINGCHU_ANNOUNCEMENT_IMAGE_CACHE_DIR`` using a Windows-style
    drive letter on a Linux / WSL2 host triggers the startup warning.
    """
    from unittest.mock import patch

    fake_config = MagicMock()
    fake_config.announcement_image_cache_dir = MagicMock()
    fake_config.announcement_image_cache_dir.__str__ = MagicMock(
        return_value="C:/dev/lingchu-bot/.local/napcat-announcement-images"
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


@pytest.mark.asyncio
async def test_startup_logs_when_install_schemas_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mocks = _apply_default_startup_mocks(monkeypatch)
    monkeypatch.setattr(
        startup_module, "install_schemas", AsyncMock(side_effect=RuntimeError("boom"))
    )

    await startup_module.startup()

    mocks["log_exception"].assert_any_call("Failed to install TOML schemas")
    mocks["initialize_scheduler_service"].assert_awaited_once()


@pytest.mark.asyncio
async def test_startup_logs_when_announcement_path_bridge_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mocks = _apply_default_startup_mocks(monkeypatch)
    monkeypatch.setattr(
        startup_module,
        "_check_announcement_image_path_bridge",
        AsyncMock(side_effect=RuntimeError("bridge boom")),
    )

    await startup_module.startup()

    mocks["log_exception"].assert_any_call(
        "Failed to run announcement image path bridge self-check"
    )
    mocks["initialize_scheduler_service"].assert_awaited_once()


@pytest.mark.asyncio
async def test_startup_logs_when_ensure_menu_config_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mocks = _apply_default_startup_mocks(monkeypatch)
    monkeypatch.setattr(
        startup_module,
        "ensure_menu_config_file_async",
        AsyncMock(side_effect=RuntimeError("menu boom")),
    )

    await startup_module.startup()

    mocks["log_exception"].assert_any_call("Failed to ensure menu config file")
    mocks["initialize_scheduler_service"].assert_awaited_once()


@pytest.mark.asyncio
async def test_startup_logs_when_handle_config_files_fail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mocks = _apply_default_startup_mocks(monkeypatch)
    mocks["handle_manager_mock"].ensure_config_files = AsyncMock(
        side_effect=RuntimeError("handle files boom")
    )

    await startup_module.startup()

    mocks["log_exception"].assert_any_call("Failed to ensure handle config files")
    mocks["initialize_scheduler_service"].assert_awaited_once()


@pytest.mark.asyncio
async def test_startup_logs_when_load_menu_config_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mocks = _apply_default_startup_mocks(monkeypatch)
    monkeypatch.setattr(
        startup_module,
        "load_menu_config",
        AsyncMock(side_effect=RuntimeError("menu load boom")),
    )

    await startup_module.startup()

    mocks["log_exception"].assert_any_call("Failed to load menu config")
    mocks["initialize_scheduler_service"].assert_awaited_once()


@pytest.mark.asyncio
async def test_startup_logs_when_initialize_handle_config_manager_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mocks = _apply_default_startup_mocks(monkeypatch)
    monkeypatch.setattr(
        startup_module,
        "initialize_handle_config_manager",
        AsyncMock(side_effect=RuntimeError("handle manager boom")),
    )

    await startup_module.startup()

    mocks["log_exception"].assert_any_call("Failed to initialize handle config manager")
    mocks["initialize_scheduler_service"].assert_awaited_once()


@pytest.mark.asyncio
async def test_startup_logs_ignored_adapters_when_registered_adapters_not_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mocks = _apply_default_startup_mocks(monkeypatch)
    monkeypatch.setattr(
        startup_module, "resolve_enabled_adapters", lambda: {"~onebot.v11"}
    )
    monkeypatch.setattr(
        startup_module,
        "resolve_registered_adapters",
        lambda _names: {"~onebot.v11", "~milky.v11"},
    )
    log_debug = MagicMock()
    monkeypatch.setattr(startup_module.logger, "debug", log_debug)

    await startup_module.startup()

    ignored_calls = [
        call
        for call in log_debug.call_args_list
        if call.args and "Lingchu 忽略未选中的已注册适配器" in call.args[0]
    ]
    assert len(ignored_calls) == 1
    mocks["initialize_scheduler_service"].assert_awaited_once()
