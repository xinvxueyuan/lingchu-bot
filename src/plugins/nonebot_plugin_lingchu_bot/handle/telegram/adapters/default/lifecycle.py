"""Telegram lifecycle handlers.

Note: do NOT add `from __future__ import annotations` here. NoneBot resolves
handler signature forward refs via the wrapper's __globals__ (common.py), which
cannot see Telegram event types. Use real type objects like the OneBot V11 siblings.
"""

from typing import Any

from nonebot import require
from nonebot.adapters.telegram import Bot
from nonebot.adapters.telegram.event import (
    GroupMessageEvent as TelegramGroupMessageEvent,
    PrivateMessageEvent as TelegramPrivateMessageEvent,
)

require("nonebot_plugin_orm")
from nonebot_plugin_orm import async_scoped_session

from .....i18n import _async as _
from .....services.restart_app import register_pending_restart_app
from ....qq.commands.common import selected_adapter_handle
from ....qq.commands.lifecycle import restart_app_cmd


@selected_adapter_handle(restart_app_cmd, "~telegram", "restart_app")
async def telegram_restart_app(
    bot: Bot,
    event: TelegramPrivateMessageEvent | TelegramGroupMessageEvent,
    session: async_scoped_session,
) -> Any:
    del session
    bot_id = str(getattr(bot, "self_id", ""))
    if isinstance(event, TelegramPrivateMessageEvent):
        conversation_type = "private"
    else:
        conversation_type = "group"
    conversation_id = str(event.chat.id)
    account_id = str(event.from_.id)
    await restart_app_cmd.send(
        (
            await _(
                "确认要重启应用吗？回复「是」确认，回复「否」取消，{seconds} 秒内有效"
            )
        ).format(seconds=60)
    )
    register_pending_restart_app(
        platform_id="telegram",
        adapter_id="~telegram",
        bot_id=bot_id,
        conversation_type=conversation_type,
        conversation_id=conversation_id,
        account_id=account_id,
    )
    return None
