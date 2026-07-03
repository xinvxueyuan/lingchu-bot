from __future__ import annotations

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.hooks.interfaces import (
    HookContext,
    HookType,
)
from src.plugins.nonebot_plugin_lingchu_bot.hooks.registry import (
    get_handlers_by_type,
    iter_handlers,
    register_handler,
)


async def _handler_a(context: HookContext) -> None:
    _ = context


async def _handler_b(context: HookContext) -> None:
    _ = context


async def _handler_c(context: HookContext) -> None:
    _ = context


@pytest.fixture(autouse=True)
def _clear_registry(monkeypatch: pytest.MonkeyPatch) -> None:
    from src.plugins.nonebot_plugin_lingchu_bot.hooks import registry as registry_mod

    monkeypatch.setattr(
        registry_mod,
        "_handlers",
        {hook_type: [] for hook_type in HookType},
    )


def test_register_and_iter_handlers() -> None:
    register_handler(HookType.MESSAGE_STORE, _handler_a)
    handlers = list(iter_handlers(HookType.MESSAGE_STORE))
    assert handlers == [_handler_a]


def test_get_handlers_by_type_empty() -> None:
    assert get_handlers_by_type(HookType.API_AUDIT) == ()


def test_disabled_handler_filtered() -> None:
    register_handler(HookType.BOT_CONNECTION, _handler_b, enabled=False)
    assert list(iter_handlers(HookType.BOT_CONNECTION)) == []
    assert get_handlers_by_type(HookType.BOT_CONNECTION) == ()


def test_iter_handlers_all_types() -> None:
    register_handler(HookType.MESSAGE_STORE, _handler_a)
    register_handler(HookType.API_AUDIT, _handler_c)
    handlers = list(iter_handlers())
    assert _handler_a in handlers
    assert _handler_c in handlers
    assert _handler_b not in handlers
