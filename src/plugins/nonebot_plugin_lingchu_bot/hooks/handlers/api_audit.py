"""API audit runtime hook handlers."""

from __future__ import annotations

from typing import Any

from nonebot.adapters import Bot

from ...core.async_utils import fire_and_forget
from ...core.runtime_config import runtime_config
from ...services.message_store import handle_api_called
from ..adapters import resolve_platform_context


@Bot.on_calling_api
async def on_calling_api(
    bot: Bot,
    api: str,
    data: dict[str, Any],
) -> None:
    """Reserved API pre-call hook for future correlation identifiers."""
    _ = (bot, api, data)


@Bot.on_called_api
async def on_called_api(
    bot: Bot,
    exception: Exception | None,
    api: str,
    data: dict[str, Any],
    result: Any,
) -> None:
    """Record platform API call results when configured."""
    if (
        not runtime_config.message_store_enabled
        or not runtime_config.message_store_record_api_calls
    ):
        return
    platform_context = resolve_platform_context(bot)
    if platform_context is None:
        return
    fire_and_forget(
        handle_api_called(platform_context, exception, api, data, result),
        name="record_api_call",
    )
