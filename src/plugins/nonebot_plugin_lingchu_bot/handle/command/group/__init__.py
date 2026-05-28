from importlib import import_module
from typing import Any

from nonebot import logger

from ....i18n import _async as _

__all__ = ("import_handle",)

for module_name in ("announcement", "lifecycle", "member", "profile"):
    import_module(f"{__name__}.{module_name}")


async def import_handle() -> Any:
    """
    导入并触发 group 处理器的初始化提示。

    该协程在运行时记录一条调试级别的本地化日志，提示“导入group处理器...”。
    """
    logger.debug(await _("导入group处理器..."))
