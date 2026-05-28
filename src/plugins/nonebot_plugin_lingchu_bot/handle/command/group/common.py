from collections.abc import Awaitable, Callable
from typing import Any

from nonebot import logger
from nonebot.adapters.milky.event import GroupMessageEvent as MilkyGroupMessageEvent
from nonebot.adapters.milky.exception import ActionFailed, NetworkError
from nonebot.adapters.onebot.v11.event import (
    GroupMessageEvent as Onebot11GroupMessageEvent,
)
from nonebot.adapters.onebot.v11.exception import (
    ActionFailed as Onebot11ActionFailed,
)
from nonebot.internal.matcher.matcher import Matcher
from nonebot_plugin_alconna import AlconnaMatcher
from nonebot_plugin_alconna.uniseg import At

from ....i18n import _async as _

type GroupCommand = type[AlconnaMatcher | Matcher]
type GroupAction = Callable[[], Awaitable[Any]]


def skip_to_protocol_exception_milky(
    command: GroupCommand,
) -> Callable[[Callable[..., Awaitable[Any]]], Callable[..., Awaitable[Any]]]:
    """
    装饰器，将被装饰的函数替换为直接发送"协议端功能异常，等待上游修复"消息
    并结束匹配器的操作。

    适用于上游协议存在 bug 时，临时跳过业务逻辑并返回统一错误信息。

    Parameters:
        command (GroupCommand): 用于调用 finish 来结束匹配器并发送回复的
        命令/匹配器类型实例。

    Returns:
        替换原函数实现的装饰器。
    """

    def decorator(func: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:  # noqa: ARG001
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            event: MilkyGroupMessageEvent | None = kwargs.get("event") or next(
                (arg for arg in args if isinstance(arg, MilkyGroupMessageEvent)),
                None,
            )
            if event is None:
                logger.error(
                    "skip_to_protocol_exception_milky: 未找到有效的 event 参数"
                )
                msg = (
                    "skip_to_protocol_exception_milky: "
                    "未找到有效的 MilkyGroupMessageEvent 参数"
                )
                raise ValueError(msg)
            return await command.finish(
                group_id=event.data.peer_id,
                message=await _("协议端功能异常，等待上游修复"),
            )

        return wrapper

    return decorator


def skip_to_protocol_exception_onebot11(
    command: GroupCommand,
) -> Callable[[Callable[..., Awaitable[Any]]], Callable[..., Awaitable[Any]]]:
    """
    装饰器，将被装饰的函数替换为直接发送"协议端功能异常，等待上游修复"消息
    并结束匹配器的操作。

    适用于上游协议存在 bug 时，临时跳过业务逻辑并返回统一错误信息。

    Parameters:
        command (GroupCommand): 用于调用 finish 来结束匹配器并发送回复的
        命令/匹配器类型实例。

    Returns:
        替换原函数实现的装饰器。
    """

    def decorator(func: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:  # noqa: ARG001
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            event: Onebot11GroupMessageEvent | None = kwargs.get("event") or next(
                (arg for arg in args if isinstance(arg, Onebot11GroupMessageEvent)),
                None,
            )
            if event is None:
                logger.error(
                    "skip_to_protocol_exception_onebot11: 未找到有效的 event 参数"
                )
                msg = (
                    "skip_to_protocol_exception_onebot11: "
                    "未找到有效的 Onebot11GroupMessageEvent 参数"
                )
                raise ValueError(msg)
            return await command.finish(
                group_id=event.group_id,
                message=await _("协议端功能异常，等待上游修复"),
            )

        return wrapper

    return decorator


def target_user_milky(user: At, event: MilkyGroupMessageEvent) -> tuple[int, str]:
    """
    解析 At 对象的 target 为用户 ID，并从群消息的 segments 中查找对应的
    mention 来确定返回的显示名。

    优先使用 user.display，若为空则尝试从 event.data.segments 中查找
    与该用户 ID 匹配的 mention 并返回其 name。

    Parameters:
        user (At): 含有 target 和 display 的 At 对象。
        event (MilkyGroupMessageEvent): 群消息事件，函数会在其
        data.segments 中查找 mention.

    Returns:
        tuple[int, str]: (目标用户 ID, 用于显示的用户名)
    """
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
        return target_user_id, mention["data"].get("name") or ""
    return target_user_id, ""


def target_user_onebot11(user: At, event: Onebot11GroupMessageEvent) -> tuple[int, str]:
    """
    解析 At 对象的 target 为用户 ID，并从群消息的原始数据中查找对应的
    mention 来确定返回的显示名。

    优先使用 user.display，若为空则尝试从 event.message 中查找
    与该用户 ID 匹配的 mention 并返回其 name。

    Parameters:
        user (At): 含有 target 和 display 的 At 对象。
        event (Onebot11GroupMessageEvent): 群消息事件，函数会在其
        message 中查找 mention.

    Returns:
        tuple[int, str]: (目标用户 ID, 用于显示的用户名)
    """
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
            and segment.data.get("data", {}).get("user_id")
            and str(segment.data["data"]["user_id"]) == str(target_user_id)
        ):
            mention_name = segment.data.get("data", {}).get("name")
            break

    if mention_name:
        return target_user_id, mention_name
    return target_user_id, ""


async def finish_action_error_milky(
    command: GroupCommand,
    operation: str,
    error: ActionFailed | NetworkError,
) -> Any:
    """
    根据异常类型记录错误并通过命令对象结束匹配器，发送对应的失败提示消息。

    Parameters:
        command (GroupCommand): 用于调用 finish 来结束匹配器并发送回复的
        命令/匹配器类型实例。
        operation (str): 发生错误的操作名称，用于构造提示消息中的操作描述。
        error (ActionFailed | NetworkError): 导致操作失败的异常；`NetworkError`
        表示网络异常，其他情况视为操作被拒绝。

    Returns:
        Any: 调用 `command.finish(...)` 的返回值（由匹配器的 `finish` 方法返回的结果）。
    """
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
    """
    执行指定的群聊异步操作并根据结果结束命令。

    Parameters:
        command (GroupCommand): 要结束的匹配器类型实例，用于调用 `finish` 发送回复。
        operation (str): 操作名称，用于构建失败时的提示信息。
        action (GroupAction): 无参数的异步可调用，执行具体操作。
        success_message (str): 操作成功时发送并记录的消息。

    Returns:
        Any: 调用 `command.finish(...)` 或 `finish_action_error_milky(...)` 的返回值。
    """
    try:
        await action()
    except (ActionFailed, NetworkError) as error:
        return await finish_action_error_milky(command, operation, error)

    logger.info(success_message)
    return await command.finish(message=success_message)


async def finish_action_error_onebot11(
    command: GroupCommand,
    operation: str,
    error: Onebot11ActionFailed,
) -> Any:
    """
    根据 OneBot11 异常类型记录错误并通过命令对象结束匹配器，
    发送对应的失败提示消息。

    Parameters:
        command (GroupCommand): 用于调用 finish 来结束匹配器并发送回复的
        命令/匹配器类型实例。
        operation (str): 发生错误的操作名称，用于构造提示消息中的操作描述。
        error (Onebot11ActionFailed): 导致操作失败的异常。

    Returns:
        Any: 调用 `command.finish(...)` 的返回值（由匹配器的 `finish` 方法返回的结果）。
    """
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
    """
    执行指定的群聊异步操作并根据结果结束命令（OneBot11 版本）。

    Parameters:
        command (GroupCommand): 要结束的匹配器类型实例，用于调用 `finish` 发送回复。
        operation (str): 操作名称，用于构建失败时的提示信息。
        action (GroupAction): 无参数的异步可调用，执行具体操作。
        success_message (str): 操作成功时发送并记录的消息。

    Returns:
        Any: 调用 `command.finish(...)` 或
        `finish_action_error_onebot11(...)` 的返回值。
    """
    try:
        await action()
    except Onebot11ActionFailed as error:
        return await finish_action_error_onebot11(command, operation, error)

    logger.info(success_message)
    return await command.finish(message=success_message)
