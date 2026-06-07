from collections.abc import Callable
from importlib import import_module
from typing import Any

from nonebot import logger

from ....i18n import _async as _
from ....platforms import resolve_enabled_adapters

__all__ = ("import_handle",)

_ADAPTER_SUBMODULES: dict[str, tuple[str, ...]] = {
    "~onebot.v11": ("onebot_v11",),
    "~milky": ("milky",),
}
_loaded_handlers: dict[str, tuple[Callable[[], Any], ...]] = {}


def _load_adapter_handlers(adapter_id: str) -> tuple[Callable[[], Any], ...]:
    if adapter_id in _loaded_handlers:
        return _loaded_handlers[adapter_id]

    handlers: list[Callable[[], Any]] = []
    for module_name in _ADAPTER_SUBMODULES.get(adapter_id, ()):
        mod = import_module(f"{__name__}.{module_name}")
        if hasattr(mod, "import_handle"):
            handlers.append(mod.import_handle)
    _loaded_handlers[adapter_id] = tuple(handlers)
    return _loaded_handlers[adapter_id]


async def import_handle() -> Any:
    """
    导入并触发 group 下所有子处理器的初始化。

    该协程依次调用各子模块的 import_handle，确保所有命令处理器完成注册。
    """
    logger.debug(await _("导入group处理器..."))
    for adapter_id in sorted(resolve_enabled_adapters()):
        handlers = _load_adapter_handlers(adapter_id)
        if not handlers:
            logger.debug(
                (await _("Lingchu 未为适配器 {adapter_id} 声明 group 处理器")).format(
                    adapter_id=adapter_id
                )
            )
            continue
        logger.debug(
            (await _("Lingchu 为适配器 {adapter_id} 导入 group 处理器")).format(
                adapter_id=adapter_id
            )
        )
        for handler in handlers:
            await handler()
