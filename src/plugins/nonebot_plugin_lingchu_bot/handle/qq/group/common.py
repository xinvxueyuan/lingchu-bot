from collections.abc import Awaitable, Callable
from functools import wraps
from typing import Any

from nonebot.adapters import Bot, Event
from nonebot.internal.matcher.matcher import Matcher
from nonebot_plugin_alconna import AlconnaMatcher

from ....platforms import is_adapter_enabled
from ....services.permissions import (
    check_permission,
    command_key_for,
    permission_context_from_event,
)

type GroupCommand = type[AlconnaMatcher | Matcher]
type GroupHandler = Callable[..., Awaitable[Any]]


def selected_adapter_handle(
    command: GroupCommand,
    adapter_id: str,
) -> Callable[[GroupHandler], GroupHandler]:
    """Register a matcher handler only when Lingchu enables the adapter."""

    def decorator(func: GroupHandler) -> GroupHandler:
        if is_adapter_enabled(adapter_id):
            command.handle()(_permission_guard(command, adapter_id, func))
        return func

    return decorator


def _permission_guard(
    command: GroupCommand,
    adapter_id: str,
    func: GroupHandler,
) -> GroupHandler:
    command_key = command_key_for(command)
    if command_key is None or command_key == "permission":
        return func

    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        bot = _find_arg(Bot, args, kwargs)
        event = _find_arg(Event, args, kwargs)
        if bot is None or event is None:
            return await func(*args, **kwargs)

        context = permission_context_from_event(
            bot=bot,
            event=event,
            adapter_id=adapter_id,
            command_key=command_key,
        )
        decision = await check_permission(context)
        if not decision.allowed:
            return await command.finish(message=f"权限不足: {decision.reason}")
        return await func(*args, **kwargs)

    return wrapper


def _find_arg(
    expected_type: type[Any],
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
) -> Any | None:
    for value in kwargs.values():
        if isinstance(value, expected_type):
            return value
    for value in args:
        if isinstance(value, expected_type):
            return value
    return None
