from collections.abc import Callable
from importlib import import_module
from typing import Any

from nonebot import logger

from ....i18n import _async as _
from ....platforms import resolve_enabled_adapters

__all__ = ("import_handle", "load_adapter_handlers")

_ADAPTER_MODULES: dict[str, tuple[str, ...]] = {
    "~onebot.v11": (
        ".onebot11.default",
        ".onebot11.napcat",
    ),
}
_loaded_handlers: dict[str, tuple[Callable[[], Any], ...]] = {}


def load_adapter_handlers(
    adapter_id: str,
    adapter_modules: dict[str, tuple[str, ...]],
    package: str | None,
) -> tuple[Callable[[], Any], ...]:
    """Load and cache handler functions for the given adapter.

    Args:
        adapter_id: Adapter identifier (e.g. ``~onebot.v11``).
        adapter_modules: Mapping from adapter ID to module name tuples.
        package: Package name for relative imports.

    Returns:
        Tuple of ``import_handle`` callables found in the mapped modules.
    """
    cache_key = f"{package}:{adapter_id}"
    if cache_key in _loaded_handlers:
        return _loaded_handlers[cache_key]

    handlers: list[Callable[[], Any]] = []
    for module_name in adapter_modules.get(adapter_id, ()):
        mod = import_module(module_name, package)
        if hasattr(mod, "import_handle"):
            handlers.append(mod.import_handle)
    _loaded_handlers[cache_key] = tuple(handlers)
    return _loaded_handlers[cache_key]


async def import_handle() -> Any:
    """Import and initialize all QQ group handlers for enabled adapters."""
    for adapter_id in sorted(resolve_enabled_adapters()):
        handlers = load_adapter_handlers(adapter_id, _ADAPTER_MODULES, __package__)
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
