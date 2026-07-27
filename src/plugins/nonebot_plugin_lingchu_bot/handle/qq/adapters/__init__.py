from collections.abc import Callable
from importlib import import_module
from typing import Any, Literal

from nonebot import logger

from ....i18n import _async as _
from ....platforms import get_protocol_implementations, resolve_enabled_adapters

__all__ = ("import_handle", "load_adapter_handlers")

type HandlerKind = Literal["command", "menu"]

# Registry ``module_path`` values are logical paths relative to the plugin
# root (e.g. ``handle.qq.adapters.onebot11.default``). Resolve them to
# absolute Python import paths by prefixing the plugin's own package name,
# derived from this module's ``__name__`` (e.g.
# ``nonebot_plugin_lingchu_bot.handle.qq.adapters`` ->
# ``nonebot_plugin_lingchu_bot``). This keeps the registry free of
# hard-coded distribution names while letting ``import_module`` work
# without a relative-import ``package`` argument. ``__name__`` is used
# instead of ``__package__`` because it is always a ``str`` for a
# package's ``__init__.py`` (``__package__`` is typed as ``str | None``).
_PLUGIN_ROOT: str = __name__.partition(".handle.")[0]

_loaded_handlers: dict[str, tuple[Callable[[], Any], ...]] = {}


def _handler_modules(adapter_id: str, kind: HandlerKind) -> tuple[str, ...]:
    """Resolve absolute handler module paths for an adapter and kind.

    Reads ``_PROTOCOL_IMPLEMENTATIONS`` (the single source of truth also used
    for database seeding), so handler loading and seeding cannot drift. Each
    logical ``module_path`` is prefixed with ``_PLUGIN_ROOT`` to form an
    absolute Python import path.
    """
    impls = get_protocol_implementations(adapter_id=adapter_id)
    if kind == "command":
        return tuple(f"{_PLUGIN_ROOT}.{impl.module_path}" for impl in impls)
    return tuple(
        f"{_PLUGIN_ROOT}.{impl.module_path}.menu"
        for impl in impls
        if impl.protocol_id == "default"
    )


def load_adapter_handlers(
    adapter_id: str,
    kind: HandlerKind,
) -> tuple[Callable[[], Any], ...]:
    """Load and cache handler callables for the given adapter and kind.

    Module paths come from ``_PROTOCOL_IMPLEMENTATIONS`` and are imported as
    absolute paths — no relative-import ``package`` argument, no compatibility
    shim. Cached under ``f"{kind}:{adapter_id}"``.
    """
    cache_key = f"{kind}:{adapter_id}"
    if cache_key in _loaded_handlers:
        return _loaded_handlers[cache_key]

    handlers: list[Callable[[], Any]] = []
    for module_path in _handler_modules(adapter_id, kind):
        mod = import_module(module_path)
        if hasattr(mod, "import_handle"):
            handlers.append(mod.import_handle)
    _loaded_handlers[cache_key] = tuple(handlers)
    return _loaded_handlers[cache_key]


async def import_handle(kind: HandlerKind) -> Any:
    """Import and initialize all handlers for enabled adapters, by kind."""
    for adapter_id in sorted(resolve_enabled_adapters()):
        handlers = load_adapter_handlers(adapter_id, kind)
        if not handlers:
            no_handlers_msg = (
                await _("Lingchu 未为适配器 {adapter_id} 声明 group 处理器")
                if kind == "command"
                else await _("Lingchu 未为适配器 {adapter_id} 声明 menu 处理器")
            )
            logger.debug(no_handlers_msg.format(adapter_id=adapter_id))
            continue
        import_msg = (
            await _("Lingchu 为适配器 {adapter_id} 导入 group 处理器")
            if kind == "command"
            else await _("Lingchu 为适配器 {adapter_id} 导入 menu 处理器")
        )
        logger.debug(import_msg.format(adapter_id=adapter_id))
        for handler in handlers:
            await handler()
