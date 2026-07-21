from collections.abc import Awaitable, Callable
from functools import wraps
from typing import Any, cast

from nonebot import require
from nonebot.exception import FinishedException
from nonebot.internal.matcher.matcher import Matcher

require("nonebot_plugin_alconna")
from nonebot_plugin_alconna import AlconnaMatcher

from ....core.bot_state import is_handle_active, is_silent_mode
from ....i18n import _async as _
from ....permissions import check_permission
from ....platforms import get_platform_profile, is_adapter_enabled

type GroupCommand = type[AlconnaMatcher | Matcher]
type GroupHandler = Callable[..., Awaitable[Any]]


def selected_adapter_handle(
    command: GroupCommand,
    adapter_id: str,
    command_key: str | None = None,
    *,
    bypass_gate: bool = False,
    bypass_silent: bool = False,
) -> Callable[[GroupHandler], GroupHandler]:
    """Register a matcher handler only when Lingchu enables the adapter."""

    def decorator(func: GroupHandler) -> GroupHandler:
        if is_adapter_enabled(adapter_id):
            if command_key is not None:
                cast("Any", command)._lingchu_command_key = command_key
            profile = get_platform_profile(adapter_id)
            platform_id = profile.platform_id if profile else ""
            wrapped: GroupHandler = func
            if command_key is not None:
                wrapped = _permission_wrapper(command, wrapped, command_key)
            if not bypass_gate or not bypass_silent:
                wrapped = _state_wrapper(
                    command,
                    wrapped,
                    platform_id=platform_id,
                    check_gate=not bypass_gate,
                    check_silent=not bypass_silent,
                )
            command.handle()(wrapped)
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
        session = kwargs.get("session")
        if bot is None or event is None or session is None:
            return await func(*args, **kwargs)

        decision = await check_permission(session, command_key, bot, event)
        if not decision.allowed:
            await command.finish(await _("权限不足"))
            return None
        return await func(*args, **kwargs)

    return wrapper


def _state_wrapper(
    command: GroupCommand,
    func: GroupHandler,
    *,
    platform_id: str = "",
    check_gate: bool = True,
    check_silent: bool = True,
) -> GroupHandler:
    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        if check_gate and not is_handle_active(platform_id):
            return None
        if check_silent and is_silent_mode(platform_id):
            return await _silent_call(command, func, *args, **kwargs)
        return await func(*args, **kwargs)

    return wrapper


async def _silent_call(
    command: GroupCommand,
    func: GroupHandler,
    *args: Any,
    **kwargs: Any,
) -> Any:
    """Call func with suppressed finish messages."""
    has_own_finish = "finish" in command.__dict__
    original_finish = command.__dict__.get("finish")

    async def _suppressed_finish(_message: Any = None, **_kw: Any) -> Any:
        raise FinishedException

    cast("Any", command).finish = _suppressed_finish
    try:
        return await func(*args, **kwargs)
    finally:
        if has_own_finish:
            cast("Any", command).finish = original_finish
        elif "finish" in command.__dict__:
            delattr(command, "finish")


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
