from collections.abc import Awaitable, Callable
from typing import Any

from nonebot.internal.matcher.matcher import Matcher
from nonebot_plugin_alconna import AlconnaMatcher

from ....platforms import is_adapter_enabled

type GroupCommand = type[AlconnaMatcher | Matcher]
type GroupHandler = Callable[..., Awaitable[Any]]


def selected_adapter_handle(
    command: GroupCommand,
    adapter_id: str,
) -> Callable[[GroupHandler], GroupHandler]:
    """Register a matcher handler only when Lingchu enables the adapter."""

    def decorator(func: GroupHandler) -> GroupHandler:
        if is_adapter_enabled(adapter_id):
            command.handle()(func)
        return func

    return decorator
