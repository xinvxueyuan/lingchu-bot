from collections.abc import Awaitable, Callable
from typing import Any

from nonebot import logger
from nonebot.adapters.milky.event import GroupMessageEvent as MilkyGroupMessageEvent
from nonebot.adapters.milky.exception import ActionFailed, NetworkError
from nonebot.internal.matcher.matcher import Matcher
from nonebot_plugin_alconna import AlconnaMatcher
from nonebot_plugin_alconna.uniseg import At

from ....i18n import _async as _

type GroupCommand = type[AlconnaMatcher | Matcher]
type GroupAction = Callable[[], Awaitable[Any]]


def target_user(user: At, event: MilkyGroupMessageEvent) -> tuple[Any, str]:
    target_user_id: int = int(user.target)
    mention: dict[str, Any] | None = next(
        (item for item in event.data.segments if item.get("type") == "mention"), None
    )
    if mention:
        return mention["data"]["user_id"], mention["data"].get("name") or ""
    return target_user_id, user.display or ""


async def finish_action_error(
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


async def run_group_action(
    command: GroupCommand,
    operation: str,
    action: GroupAction,
    success_message: str,
) -> Any:
    try:
        await action()
    except (ActionFailed, NetworkError) as error:
        return await finish_action_error(command, operation, error)

    logger.info(success_message)
    return await command.finish(message=success_message)
