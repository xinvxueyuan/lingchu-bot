"""Tests for typed runtime handle-default updates."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.core import handle_default_values
from src.plugins.nonebot_plugin_lingchu_bot.core.handle_default_values import (
    HandleDefaultValueError,
    update_handle_default,
)


@pytest.mark.asyncio
async def test_update_handle_default_persists_one_typed_field() -> None:
    """A configured default update keeps the public manager boundary typed."""
    manager = MagicMock()
    manager.update_config = AsyncMock()

    value = await update_handle_default(
        "member_mute",
        "mute_duration",
        "600",
        config_manager=manager,
    )

    assert value == 600
    manager.update_config.assert_awaited_once_with(
        "member_mute", {"defaults": {"mute_duration": 600}}
    )


@pytest.mark.asyncio
async def test_update_handle_default_rejects_unknown_field() -> None:
    """Chat input cannot mutate an arbitrary TOML path."""
    with pytest.raises(HandleDefaultValueError, match="unsupported"):
        await update_handle_default("member_mute", "enabled", "false")


def test_optional_duration_accepts_permanent_literal() -> None:
    """Block defaults use a deliberate literal for persisted null durations."""
    definition = next(
        item
        for item in handle_default_values.supported_handle_defaults()
        if (item.command_key, item.field) == ("block_member", "block_duration")
    )
    assert definition.parse("永久") is None
