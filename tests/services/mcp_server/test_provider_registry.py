from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from typing import override

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.services.mcp_server.contracts import (
    BotAddress,
    ContractError,
    ErrorCode,
)
from src.plugins.nonebot_plugin_lingchu_bot.services.mcp_server.providers import (
    ProviderConflictError,
    ProviderRegistry,
)


@dataclass(frozen=True, slots=True)
class FakeProvider:
    platform_id: str
    adapter_id: str
    protocol_ids: frozenset[str]


class OrderedProtocols(frozenset[str]):
    @override
    def __iter__(self) -> Iterator[str]:
        return iter(("new", "default"))


def test_registry_resolves_provider_by_exact_platform_adapter_and_protocol() -> None:
    default = FakeProvider("qq", "~onebot.v11", frozenset({"default"}))
    napcat = FakeProvider("qq", "~onebot.v11", frozenset({"napcat"}))
    registry = ProviderRegistry((default, napcat))

    resolved = registry.resolve(BotAddress("qq", "~onebot.v11", "napcat", "10001"))

    assert resolved is napcat


def test_registry_reports_unsupported_platform_without_fallback() -> None:
    provider = FakeProvider("qq", "~onebot.v11", frozenset({"default"}))
    registry = ProviderRegistry((provider,))

    with pytest.raises(ContractError) as caught:
        registry.resolve(BotAddress("matrix", "matrix", "v1", "10001"))

    assert caught.value.code is ErrorCode.UNSUPPORTED_PLATFORM


def test_register_conflict_leaves_registry_unchanged() -> None:
    original = FakeProvider("qq", "~onebot.v11", frozenset({"default"}))
    conflicting = FakeProvider("qq", "~onebot.v11", OrderedProtocols())
    registry = ProviderRegistry((original,))

    with pytest.raises(ProviderConflictError):
        registry.register(conflicting)

    assert (
        registry.resolve(BotAddress("qq", "~onebot.v11", "default", "10001"))
        is original
    )
    with pytest.raises(ContractError) as caught:
        registry.resolve(BotAddress("qq", "~onebot.v11", "new", "10001"))
    assert caught.value.code is ErrorCode.UNSUPPORTED_PLATFORM
