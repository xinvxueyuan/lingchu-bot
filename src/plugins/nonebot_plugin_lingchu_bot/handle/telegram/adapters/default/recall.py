"""Telegram message recall handler.

Note: do NOT add `from __future__ import annotations` here. NoneBot resolves
handler signature forward refs via the wrapper's __globals__ (common.py), which
cannot see GroupMessageEvent. Use real type objects like the OneBot V11 siblings.
"""

from typing import Any

from nonebot import logger, require
from nonebot.adapters.telegram import Bot
from nonebot.adapters.telegram.event import GroupMessageEvent
from nonebot.adapters.telegram.exception import ActionFailed

require("nonebot_plugin_alconna")
from nonebot_plugin_alconna.uniseg import At

require("nonebot_plugin_orm")
from nonebot_plugin_orm import async_scoped_session

from .....i18n import _async as _
from ....qq.commands.common import selected_adapter_handle
from ....qq.commands.mute import recall_message_cmd


@selected_adapter_handle(recall_message_cmd, "~telegram", "recall_message")
async def telegram_recall_message(
    session: async_scoped_session,
    target: At | int | None = None,
    count: int | None = None,
    bot: Bot | None = None,
    event: GroupMessageEvent | None = None,
) -> Any:
    del session, target, count
    if bot is None or event is None:
        return None
    reply = event.reply_to_message
    if reply is None:
        return await recall_message_cmd.finish(await _("请回复要撤回的消息"))
    try:
        await bot.delete_message(
            chat_id=event.chat.id,
            message_id=reply.message_id,
        )
    except ActionFailed as error:
        logger.error(f"Telegram recall rejected: {error!r}")
        return await recall_message_cmd.finish(await _("撤回失败，操作被拒绝"))
    return await recall_message_cmd.finish(await _("撤回成功"))
