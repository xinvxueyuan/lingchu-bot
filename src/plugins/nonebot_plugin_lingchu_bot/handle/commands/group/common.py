from collections.abc import Awaitable, Callable
from importlib import import_module
from typing import Any

from nonebot.internal.matcher.matcher import Matcher
from nonebot_plugin_alconna import AlconnaMatcher

from ....platforms import is_adapter_enabled

type GroupCommand = type[AlconnaMatcher | Matcher]
type GroupHandler = Callable[..., Awaitable[Any]]

_LAZY_EXPORTS = {
    "finish_action_error_milky": ".milky.common",
    "run_group_action_milky": ".milky.common",
    "target_user_milky": ".milky.common",
    "finish_action_error_onebot11": ".onebot_v11.common",
    "run_group_action_onebot11": ".onebot_v11.common",
    "target_user_onebot11": ".onebot_v11.common",
}


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


def __getattr__(name: str) -> Any:
    if name not in _LAZY_EXPORTS:
        raise AttributeError(name)
    module = import_module(_LAZY_EXPORTS[name], __package__)
    value = getattr(module, name)
    globals()[name] = value
    return value
