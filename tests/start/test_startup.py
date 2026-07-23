from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

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
    log_exception = MagicMock()
    monkeypatch.setattr(startup_module.logger, "exception", log_exception)

    monkeypatch.setattr(startup_module, "ensure_llm_config_file_async", AsyncMock())
    monkeypatch.setattr(startup_module, "initialize_llm_runtime", AsyncMock())
    monkeypatch.setattr(startup_module, "initialize_mcp_agent_runtime", AsyncMock())
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

    log_exception = MagicMock()
    monkeypatch.setattr(startup_module.logger, "exception", log_exception)

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
        "initialize_mcp_agent_runtime",
        AsyncMock(side_effect=lambda: calls.append("initialize_mcp_agent_runtime")),
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
    assert calls.index("ensure_llm_config") < calls.index("initialize_llm_runtime")
    assert calls.index("initialize_llm_runtime") < calls.index("ensure_menu_config")
    assert calls.index("ensure_menu_config") < calls.index("menu_import")
    assert calls.index("set_menu_pages") < calls.index("menu_import")
    assert calls.index("set_menu_features") < calls.index("menu_import")
    if llm_error is not None:
        assert "initialize_mcp_agent_runtime" not in calls
        log_exception.assert_called_once_with(
            "Failed to initialize LLM runtime; AI is unavailable"
        )
    else:
        assert calls.index("initialize_llm_runtime") < calls.index(
            "initialize_mcp_agent_runtime"
        )
        assert calls.index("initialize_mcp_agent_runtime") < calls.index(
            "ensure_menu_config"
        )


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
