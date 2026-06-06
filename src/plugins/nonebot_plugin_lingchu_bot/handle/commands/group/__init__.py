from collections.abc import Callable
from importlib import import_module
from typing import Any

from nonebot import logger

from ....i18n import _async as _

__all__ = ("import_handle",)

_submodules = ("announcement", "lifecycle", "member", "mute", "profile")
_handlers: list[Callable[[], Any]] = []

for module_name in _submodules:
    mod = import_module(f"{__name__}.{module_name}")
    if hasattr(mod, "import_handle"):
        _handlers.append(mod.import_handle)


async def import_handle() -> Any:
    """
    导入并触发 group 下所有子处理器的初始化。

    该协程依次调用各子模块的 import_handle，确保所有命令处理器完成注册。
    """
    logger.debug(await _("导入group处理器..."))
    for handler in _handlers:
        await handler()
