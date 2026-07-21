from __future__ import annotations

from dataclasses import dataclass

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.services.mcp_server.bot_directory import (
    BotDirectory,
)
from src.plugins.nonebot_plugin_lingchu_bot.services.mcp_server.contracts import (
    BotAddress,
    ConversationAddress,
    ImageSegment,
    OperationStatus,
    SendMessageRequest,
    SendMessageResult,
    TextSegment,
)
from src.plugins.nonebot_plugin_lingchu_bot.services.mcp_server.message_send import (
    SendMessageAction,
)
from src.plugins.nonebot_plugin_lingchu_bot.services.mcp_server.providers import (
    ProviderRegistry,
)


@dataclass(slots=True)
class FakeBot:
    address: BotAddress


@dataclass(frozen=True, slots=True)
class FakeProvider:
    platform_id: str = "qq"
    adapter_id: str = "~onebot.v11"
    protocol_ids: frozenset[str] = frozenset({"default"})

    async def send_message(
        self,
        bot: object,
        request: SendMessageRequest,
    ) -> SendMessageResult:
        assert isinstance(bot, FakeBot)
        return SendMessageResult("op-1", OperationStatus.SUCCEEDED, "42")


def resolve_fake_bot(candidate: object) -> BotAddress:
    assert isinstance(candidate, FakeBot)
    return candidate.address


@pytest.mark.asyncio
async def test_send_action_resolves_the_exact_provider_and_connected_bot() -> None:
    requested_address = BotAddress("qq", "~onebot.v11", "default", "10002")
    other_address = BotAddress("qq", "~onebot.v11", "default", "10001")
    requested = FakeBot(requested_address)
    directory = BotDirectory(resolve_fake_bot)
    directory.connect(other_address, FakeBot(other_address), display_name="other")
    directory.connect(requested_address, requested, display_name="requested")
    action = SendMessageAction(ProviderRegistry((FakeProvider(),)), directory)
    request = SendMessageRequest(
        requested_address,
        ConversationAddress("group", "20002"),
        (TextSegment("hello"), ImageSegment("https://example.com/a.png")),
        "key-1",
    )

    result = await action.send_message(request)

    assert result == SendMessageResult("op-1", OperationStatus.SUCCEEDED, "42")
