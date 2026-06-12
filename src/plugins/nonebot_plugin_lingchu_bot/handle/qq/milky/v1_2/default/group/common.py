from collections.abc import Awaitable, Callable
from typing import Any

from nonebot import logger
from nonebot.adapters.milky import Bot as MilkyBot
from nonebot.adapters.milky.event import GroupMessageEvent as MilkyGroupMessageEvent
from nonebot.adapters.milky.exception import ActionFailed, NetworkError
from nonebot_plugin_alconna.uniseg import At

from .......i18n import _async as _
from .....group.common import GroupCommand

type GroupAction = Callable[[], Awaitable[Any]]


async def target_user_milky(
    user: At, bot: MilkyBot, event: MilkyGroupMessageEvent
) -> tuple[int, str]:
    try:
        target_user_id: int = int(user.target)
    except (TypeError, ValueError) as error:
        msg = f"无效的用户 ID: {user.target!r}"
        raise ValueError(msg) from error

    if user.display:
        return target_user_id, user.display

    mention: dict[str, Any] | None = next(
        (
            item
            for item in event.data.segments
            if item.get("type") == "mention"
            and str(item.get("data", {}).get("user_id")) == str(target_user_id)
        ),
        None,
    )
    if mention:
        name = mention["data"].get("name") or ""
        if name:
            return target_user_id, name

    try:
        member_info = await bot.get_group_member_info(
            group_id=event.data.peer_id, user_id=target_user_id
        )
        name = member_info.card or member_info.nickname
        if name:
            return target_user_id, name
    except (ActionFailed, NetworkError):
        logger.debug(
            f"获取群成员信息失败: "
            f"group_id={event.data.peer_id}, user_id={target_user_id}"
        )

    return target_user_id, ""


async def finish_action_error_milky(
    command: GroupCommand,
    operation: str,
    error: ActionFailed | NetworkError,
) -> Any:
    if isinstance(error, NetworkError):
        logger.error(f"{operation}失败，网络异常: {error!r}")
        return await command.finish(
            message=(await _("{operation}失败，网络异常: {error!r}")).format(
                operation=operation, error=error
            )
        )

    logger.error(f"{operation}失败，操作被拒绝: {error!r}")
    return await command.finish(
        message=(await _("{operation}失败，操作被拒绝: {error!r}")).format(
            operation=operation, error=error
        )
    )


async def run_group_action_milky(
    command: GroupCommand,
    operation: str,
    action: GroupAction,
    success_message: str,
) -> Any:
    try:
        await action()
    except (ActionFailed, NetworkError) as error:
        return await finish_action_error_milky(command, operation, error)

    logger.info(success_message)
    return await command.finish(message=success_message)
