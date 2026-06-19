from collections.abc import Awaitable, Callable
from functools import wraps
from typing import Any

from nonebot.internal.matcher.matcher import Matcher
from nonebot_plugin_alconna import AlconnaMatcher

from ....i18n import _async as _
from ....permissions import check_permission
from ....platforms import is_adapter_enabled

type GroupCommand = type[AlconnaMatcher | Matcher]
type GroupHandler = Callable[..., Awaitable[Any]]


def selected_adapter_handle(
    command: GroupCommand,
    adapter_id: str,
    command_key: str | None = None,
) -> Callable[[GroupHandler], GroupHandler]:
    """Register a matcher handler only when Lingchu enables the adapter."""

    def decorator(func: GroupHandler) -> GroupHandler:
        if is_adapter_enabled(adapter_id):
            command.handle()(_permission_wrapper(command, func, command_key))
        return func

    return decorator


def _permission_wrapper(
    command: GroupCommand,
    func: GroupHandler,
    command_key: str | None,
) -> GroupHandler:
    if command_key is None:
        return func

    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        bot = kwargs.get("bot") or _first_arg_with_attr(args, "adapter")
        event = kwargs.get("event") or kwargs.get("_event") or _first_event_arg(args)
        if bot is None or event is None:
            return await func(*args, **kwargs)

        decision = await check_permission(command_key, bot, event)
        if not decision.allowed:
            await command.finish(await _("权限不足"))
            return None
        return await func(*args, **kwargs)

    return wrapper


def _first_arg_with_attr(args: tuple[Any, ...], attr: str) -> Any | None:
    for arg in args:
        if hasattr(arg, attr):
            return arg
    return None


def _first_event_arg(args: tuple[Any, ...]) -> Any | None:
    for arg in args:
        if hasattr(arg, "user_id") or hasattr(arg, "data"):
            return arg
    return None
