from collections.abc import Awaitable, Callable
from typing import Any

from nonebot import logger
from nonebot.adapters.milky.event import GroupMessageEvent as MilkyGroupMessageEvent
from nonebot.adapters.milky.exception import ActionFailed, NetworkError
from nonebot_plugin_alconna.uniseg import At

from .....i18n import _async as _
from ..common import GroupCommand

type GroupAction = Callable[[], Awaitable[Any]]


def target_user_milky(user: At, event: MilkyGroupMessageEvent) -> tuple[int, str]:
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
        return target_user_id, mention["data"].get("name") or user.display or ""
    return target_user_id, user.display or ""


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
