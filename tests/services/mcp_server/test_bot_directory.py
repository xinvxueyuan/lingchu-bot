from __future__ import annotations

from dataclasses import dataclass

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.services.mcp_server.bot_directory import (
    BotDirectory,
)
from src.plugins.nonebot_plugin_lingchu_bot.services.mcp_server.contracts import (
    BotAddress,
    ContractError,
    ErrorCode,
)


@dataclass(slots=True)
class FakeBot:
    self_id: str
    address: BotAddress


def address(bot_id: str, *, protocol_id: str = "default") -> BotAddress:
    return BotAddress("qq", "~onebot.v11", protocol_id, bot_id)


def bot(bot_id: str, *, bot_address: BotAddress | None = None) -> FakeBot:
    return FakeBot(bot_id, bot_address or address(bot_id))


def resolve_fake_bot(candidate: object) -> BotAddress:
    assert isinstance(candidate, FakeBot)
    return candidate.address


def test_directory_resolves_the_exact_bot_when_multiple_are_connected() -> None:
    first = bot("10001")
    requested = bot("10002")
    directory = BotDirectory(resolve_fake_bot)
    directory.connect(address("10001"), first, display_name="first")
    directory.connect(address("10002"), requested, display_name="requested")

    assert directory.resolve(address("10002")) is requested


def test_directory_never_falls_back_when_any_address_part_mismatches() -> None:
    connected = bot("10001")
    directory = BotDirectory(resolve_fake_bot)
    directory.connect(address("10001"), connected, display_name="connected")

    mismatches = (
        BotAddress("matrix", "~onebot.v11", "default", "10001"),
        BotAddress("qq", "~onebot.v12", "default", "10001"),
        address("10001", protocol_id="napcat"),
        address("other"),
    )
    for requested in mismatches:
        with pytest.raises(ContractError) as caught:
            directory.resolve(requested)
        assert caught.value.code is ErrorCode.BOT_NOT_FOUND


def test_disconnect_removes_only_the_matching_connection_instance() -> None:
    old = bot("10001")
    replacement = bot("10001")
    directory = BotDirectory(resolve_fake_bot)
    directory.connect(address("10001"), old, display_name="old")
    directory.connect(address("10001"), replacement, display_name="replacement")

    assert directory.disconnect(address("10001"), old) is False
    assert directory.resolve(address("10001")) is replacement
    assert directory.disconnect(address("10001"), replacement) is True
    with pytest.raises(ContractError) as caught:
        directory.resolve(address("10001"))
    assert caught.value.code is ErrorCode.BOT_NOT_FOUND


def test_list_connected_intersects_exact_allowed_addresses_in_stable_order() -> None:
    directory = BotDirectory(resolve_fake_bot)
    second = bot("10002")
    first = bot("10001")
    directory.connect(address("10002"), second, display_name="second")
    directory.connect(address("10001"), first, display_name="first")

    summaries = directory.list_connected(
        frozenset({
            address("10002"),
            BotAddress("qq", "~onebot.v11", "other", "10001"),
        })
    )

    assert tuple(item.address for item in summaries) == (address("10002"),)


@pytest.mark.parametrize(
    "claimed",
    [
        BotAddress("matrix", "~onebot.v11", "default", "10001"),
        BotAddress("qq", "~onebot.v12", "default", "10001"),
        BotAddress("qq", "~onebot.v11", "napcat", "10001"),
        BotAddress("qq", "~onebot.v11", "default", "other"),
    ],
)
def test_connect_rejects_every_claimed_address_mismatch(claimed: BotAddress) -> None:
    directory = BotDirectory(resolve_fake_bot)

    with pytest.raises(ContractError) as caught:
        directory.connect(claimed, bot("10001"), display_name="forged")

    assert caught.value.code is ErrorCode.INVALID_IDENTIFIER
    with pytest.raises(ContractError) as missing:
        directory.resolve(claimed)
    assert missing.value.code is ErrorCode.BOT_NOT_FOUND
