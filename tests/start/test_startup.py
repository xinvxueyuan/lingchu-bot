from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, call

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.schema import CreateTable

from src.plugins.nonebot_plugin_lingchu_bot.database.models import (
    IdentityMembership,
    IdentityUser,
    PlatformAccount,
)
from src.plugins.nonebot_plugin_lingchu_bot.hooks.handlers import (
    lifecycle as lifecycle_module,
)
from src.plugins.nonebot_plugin_lingchu_bot.repositories import (
    permissions as permission_repo,
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
    log_error = MagicMock()
    monkeypatch.setattr(startup_module.logger, "error", log_error)

    handle_manager_mock = MagicMock()
    handle_manager_mock.ensure_config_files = AsyncMock()
    handle_manager_mock.get_all_configs = AsyncMock()
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
    set_menu_pages = MagicMock()
    set_menu_features = MagicMock()
    monkeypatch.setattr(startup_module.menu_module, "set_menu_pages", set_menu_pages)
    monkeypatch.setattr(
        startup_module.menu_module,
        "set_menu_features",
        set_menu_features,
    )
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
    import_handle_mock = AsyncMock()
    monkeypatch.setattr(startup_module, "import_handle", import_handle_mock)
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
        "log_error": log_error,
        "handle_manager_mock": handle_manager_mock,
        "set_menu_pages": set_menu_pages,
        "set_menu_features": set_menu_features,
        "import_handle": import_handle_mock,
        "register_scheduler_handler": register_scheduler_handler,
        "initialize_scheduler_service": initialize_scheduler_service,
    }


@pytest.mark.asyncio
async def test_startup_imports_group_and_menu_handlers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    import_handle_mock = AsyncMock(
        side_effect=lambda kind: calls.append(f"import_handle:{kind}")
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
    handle_manager_mock = MagicMock()
    handle_manager_mock.ensure_config_files = AsyncMock()
    handle_manager_mock.get_all_configs = AsyncMock(
        side_effect=lambda: calls.append("load_handle_configs")
    )
    monkeypatch.setattr(
        startup_module, "get_handle_config_manager", lambda: handle_manager_mock
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
    monkeypatch.setattr(startup_module, "import_handle", import_handle_mock)
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

    assert import_handle_mock.await_count == 2
    assert import_handle_mock.call_args_list == [
        call("command"),
        call("menu"),
    ]
    register_scheduler_handler.assert_called_once_with(
        startup_module.SCHEDULER_CLEANUP_HANDLER_KEY,
        startup_module.cleanup_expired_messages,
    )
    initialize_scheduler_service.assert_awaited_once()
    handle_manager_mock.get_all_configs.assert_awaited_once_with()
    handle_manager_mock.ensure_config_files.assert_not_awaited()
    assert calls.index("load_handle_configs") < calls.index("import_handle:menu")
    assert calls.index("set_menu_pages") < calls.index("import_handle:menu")
    assert calls.index("set_menu_features") < calls.index("import_handle:menu")


@pytest.mark.asyncio
async def test_startup_commits_registry_and_permission_seeds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mocks = _apply_default_startup_mocks(monkeypatch)
    session = MagicMock()
    transaction = AsyncMock()
    session.begin.return_value = transaction
    session_context = AsyncMock()
    session_context.__aenter__.return_value = session
    monkeypatch.setattr(startup_module, "get_session", lambda: session_context)
    seed_registry = AsyncMock()
    seed_permissions = AsyncMock()
    monkeypatch.setattr(startup_module, "seed_registry_tables", seed_registry)
    monkeypatch.setattr(
        startup_module,
        "validate_and_seed_permission_system",
        seed_permissions,
    )

    await startup_module.startup()

    session.begin.assert_called_once_with()
    transaction.__aenter__.assert_awaited_once_with()
    transaction.__aexit__.assert_awaited_once()
    seed_registry.assert_awaited_once_with(session)
    seed_permissions.assert_awaited_once_with(session)
    mocks["initialize_scheduler_service"].assert_awaited_once()


@pytest.mark.asyncio
async def test_startup_seeded_superuser_is_visible_to_a_new_session(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _apply_default_startup_mocks(monkeypatch)
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'permissions.db'}")
    tables = (
        IdentityUser.__table__,
        PlatformAccount.__table__,
        IdentityMembership.__table__,
    )
    async with engine.begin() as connection:
        for table in tables:
            await connection.execute(CreateTable(table))
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr(startup_module, "get_session", session_factory)
    monkeypatch.setattr(startup_module, "seed_registry_tables", AsyncMock())

    async def seed_permissions(session: AsyncSession) -> None:
        await permission_repo.upsert_identity_user(session, "owner", "Owner")
        await permission_repo.bind_platform_account(
            session,
            uid="owner",
            platform_id="qq",
            account_id="42",
            display_name="Owner",
        )
        await permission_repo.upsert_membership(
            session,
            uid="owner",
            group_id=permission_repo.SUPERUSERS_GROUP_ID,
            source=permission_repo.SUPERUSER_SOURCE,
        )

    monkeypatch.setattr(
        startup_module,
        "validate_and_seed_permission_system",
        seed_permissions,
    )

    try:
        await startup_module.startup()

        async with session_factory() as verification_session:
            user = await permission_repo.get_user_by_platform_account(
                verification_session,
                "qq",
                "42",
            )
            assert user is not None
            assert user.uid == "owner"
            assert await permission_repo.is_superuser(verification_session, user.uid)
    finally:
        await engine.dispose()


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
async def test_startup_does_not_create_runtime_config_files(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mocks = _apply_default_startup_mocks(monkeypatch)

    await startup_module.startup()

    mocks["handle_manager_mock"].ensure_config_files.assert_not_awaited()
    mocks["handle_manager_mock"].get_all_configs.assert_awaited_once_with()
    mocks["initialize_scheduler_service"].assert_awaited_once()


@pytest.mark.asyncio
async def test_startup_uses_menu_defaults_when_config_is_invalid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mocks = _apply_default_startup_mocks(monkeypatch)
    monkeypatch.setattr(
        startup_module,
        "load_menu_config",
        AsyncMock(
            side_effect=startup_module.MenuConfigError(
                Path("menu.toml"), ValueError("invalid menu")
            )
        ),
    )

    await startup_module.startup()

    mocks["log_error"].assert_called_once()
    assert "using in-memory defaults" in mocks["log_error"].call_args.args[0]
    mocks["set_menu_pages"].assert_called_with(
        startup_module.menu_module._DEFAULT_MENU_PAGES
    )
    mocks["set_menu_features"].assert_called_with(
        startup_module.menu_module._DEFAULT_MENU_FEATURES
    )
    mocks["initialize_scheduler_service"].assert_awaited_once()


@pytest.mark.asyncio
async def test_startup_logs_when_load_menu_config_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mocks = _apply_default_startup_mocks(monkeypatch)
    monkeypatch.setattr(
        startup_module,
        "load_menu_config",
        AsyncMock(
            side_effect=startup_module.MenuConfigError(
                Path("menu.toml"), ValueError("menu load boom")
            )
        ),
    )

    await startup_module.startup()

    mocks["log_error"].assert_called_once()
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
