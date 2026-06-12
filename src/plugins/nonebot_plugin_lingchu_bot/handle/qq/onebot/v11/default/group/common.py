from collections.abc import Awaitable, Callable
from typing import Any

from nonebot import logger
from nonebot.adapters.onebot.v11 import Bot as Onebot11Bot
from nonebot.adapters.onebot.v11.event import (
    GroupMessageEvent as Onebot11GroupMessageEvent,
)
from nonebot.adapters.onebot.v11.exception import (
    ActionFailed as Onebot11ActionFailed,
)
from nonebot_plugin_alconna.uniseg import At

from .......i18n import _async as _
from .....group.common import GroupCommand

type GroupAction = Callable[[], Awaitable[Any]]


async def target_user_onebot11(
    user: At, bot: Onebot11Bot, event: Onebot11GroupMessageEvent
) -> tuple[int, str]:
    try:
        target_user_id: int = int(user.target)
    except (TypeError, ValueError) as error:
        msg = f"无效的用户 ID: {user.target!r}"
        raise ValueError(msg) from error

    if user.display:
        return target_user_id, user.display

    try:
        member_info = await bot.get_group_member_info(
            group_id=event.group_id, user_id=target_user_id
        )
        name = member_info.get("card") or member_info.get("nickname") or ""
        if name:
            return target_user_id, str(name)
    except Onebot11ActionFailed:
        logger.debug(
            f"获取群成员信息失败: group_id={event.group_id}, user_id={target_user_id}"
        )

    return target_user_id, ""


async def finish_action_error_onebot11(
    command: GroupCommand,
    operation: str,
    error: Onebot11ActionFailed,
) -> Any:
    logger.error(f"{operation}失败，操作被拒绝: {error!r}")
    return await command.finish(
        message=(await _("{operation}失败，操作被拒绝: {error!r}")).format(
            operation=operation, error=error
        )
    )


async def run_group_action_onebot11(
    command: GroupCommand,
    operation: str,
    action: GroupAction,
    success_message: str,
) -> Any:
    try:
        await action()
    except Onebot11ActionFailed as error:
        return await finish_action_error_onebot11(command, operation, error)

    logger.info(success_message)
    return await command.finish(message=success_message)
