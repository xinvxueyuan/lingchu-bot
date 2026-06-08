from collections.abc import Awaitable, Callable
from typing import Any

from nonebot import logger
from nonebot.adapters.onebot.v11.event import (
    GroupMessageEvent as Onebot11GroupMessageEvent,
)
from nonebot.adapters.onebot.v11.exception import (
    ActionFailed as Onebot11ActionFailed,
)
from nonebot_plugin_alconna.uniseg import At

from .....i18n import _async as _
from ..common import GroupCommand

type GroupAction = Callable[[], Awaitable[Any]]


def target_user_onebot11(
    user: At, event: Onebot11GroupMessageEvent
) -> tuple[int, str | None]:
    try:
        target_user_id: int = int(user.target)
    except (TypeError, ValueError) as error:
        msg = f"无效的用户 ID: {user.target!r}"
        raise ValueError(msg) from error

    if user.display:
        return target_user_id, user.display

    mention_name: str | None = None
    for segment in event.message:
        if (
            segment.type == "at"
            and segment.data.get("qq")
            and str(segment.data["qq"]) == str(target_user_id)
        ):
            mention_name = segment.data.get("name")
            break

    if mention_name:
        return target_user_id, mention_name
    return target_user_id, None


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
