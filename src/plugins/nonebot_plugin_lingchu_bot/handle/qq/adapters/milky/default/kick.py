from typing import Any

from nonebot import logger
from nonebot.adapters.milky import Bot as MilkyBot
from nonebot.adapters.milky.event import (
    GroupMessageEvent as MilkyGroupMessageEvent,
)
from nonebot.adapters.milky.exception import ActionFailed as MilkyActionFailed
from nonebot_plugin_alconna.uniseg import At

from ......database.orm_crud import DatabaseError
from ......i18n import _async as _
from ......repositories.blocklist import find_active_block
from ....commands.common import selected_adapter_handle
from ....commands.kick import kick_member_cmd
from .common import resolve_user_milky

QQ_PLATFORM_ID = "qq"
MILKY_ADAPTER_ID = "~milky"


def _bot_id(bot: MilkyBot) -> str:
    return str(getattr(bot, "self_id", ""))


async def _kick_member(
    *,
    command: type[Any],
    user: At | int,
    reason: str | None,
    bot: MilkyBot,
    event: MilkyGroupMessageEvent,
) -> Any:
    """踢出群成员核心逻辑"""
    # 解析用户
    target_user_id, target_name = await resolve_user_milky(user, bot, event)

    # 不能踢自己
    if target_user_id == event.data.sender.user_id:
        return await command.finish(await _("不能踢出自己"))

    # 不能踢机器人
    try:
        bot_self_id = int(bot.self_id)
    except (ValueError, TypeError):
        bot_self_id = None
    if bot_self_id is not None and target_user_id == bot_self_id:
        return await command.finish(await _("不能踢出机器人"))

    # 检查目标用户是否在黑名单中
    try:
        entry = await find_active_block(
            platform_id=QQ_PLATFORM_ID,
            adapter_id=MILKY_ADAPTER_ID,
            bot_id=_bot_id(bot),
            group_id=event.data.peer_id,
            user_id=target_user_id,
        )
    except DatabaseError as error:
        logger.error(f"查询黑名单失败，数据库异常: {error!r}")
        return await command.finish(await _("查询黑名单失败，数据库异常"))

    if entry is None:
        display_name = target_name or str(target_user_id)
        message = await _("用户 {name} 不在黑名单中，无法执行踢出操作")
        return await command.finish(message.format(name=display_name))

    # 执行踢出操作
    try:
        await bot.kick_group_member(
            group_id=event.data.peer_id,
            user_id=target_user_id,
            reject_add_request=False,
        )
    except MilkyActionFailed as e:
        logger.error(f"踢出群成员失败: {e!r}")
        return await command.finish(await _("踢出群成员失败，操作被拒绝"))

    # 反馈结果
    display_name = target_name or str(target_user_id)
    reason_text = f"，原因: {reason}" if reason else ""
    message = await _("已踢出群成员 {name}{reason}")
    return await command.finish(message.format(name=display_name, reason=reason_text))


@selected_adapter_handle(kick_member_cmd, "~milky", "kick_member")
async def milkybot_kick_member(
    user: At | int,
    bot: MilkyBot,
    event: MilkyGroupMessageEvent,
    reason: str | None = None,
) -> Any:
    """Milky 踢出群成员处理器"""
    return await _kick_member(
        command=kick_member_cmd,
        user=user,
        reason=reason,
        bot=bot,
        event=event,
    )
