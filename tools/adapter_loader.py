"""停维适配器按需加载工具。

此模块提供独立于启动流程的适配器加载能力，
用于按需加载已停维适配器的 handler 模块。

使用示例::

    from tools.adapter_loader import load_deprecated_adapter

    # 按需加载停维适配器
    load_deprecated_adapter("~qq")
"""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, Any

from nonebot import logger

if TYPE_CHECKING:
    from collections.abc import Callable

# 停维适配器的模块映射表
# 这些适配器已从启动流程中移除，但源码保留以备未来复用
# 注意：~milky、~qq、~onebot.v12 仅供停维检查，无 handler 模块。
_DEPRECATED_ADAPTER_MODULES: dict[str, tuple[str, ...]] = {}

_DEPRECATED_MENU_MODULES: dict[str, tuple[str, ...]] = {}

# 所有停维适配器 ID 列表，与 registry._DEPRECATED_ADAPTER_IDS 保持一致。
_DEPRECATED_ADAPTER_IDS: tuple[str, ...] = ("~milky", "~qq", "~onebot.v12")


def load_deprecated_adapter(adapter_id: str) -> tuple[Callable[..., Any], ...]:
    """按需加载停维适配器的 handler 模块。

    Args:
        adapter_id: 适配器 ID，如 ``~qq``

    Returns:
        已加载模块的 ``import_handle`` 函数元组

    Raises:
        ValueError: 如果指定的适配器不在停维列表中
    """
    modules = _DEPRECATED_ADAPTER_MODULES.get(adapter_id)
    if modules is None:
        msg = (
            f"适配器 {adapter_id!r} 不在停维列表中。"
            f"可用: {', '.join(sorted(_DEPRECATED_ADAPTER_MODULES))}"
        )
        raise ValueError(msg)

    handlers: list[Callable[..., Any]] = []
    for module_path in modules:
        mod = import_module(module_path)
        if hasattr(mod, "import_handle"):
            handlers.append(mod.import_handle)
        logger.info(f"已加载停维适配器模块: {module_path}")

    return tuple(handlers)


async def load_and_init_deprecated_adapter(adapter_id: str) -> None:
    """按需加载并初始化停维适配器的 handler 模块。

    Args:
        adapter_id: 适配器 ID，如 ``~qq``
    """
    handlers = load_deprecated_adapter(adapter_id)
    for handler in handlers:
        await handler()


def list_deprecated_adapters() -> tuple[str, ...]:
    """返回所有停维适配器 ID 列表。"""
    return tuple(sorted(_DEPRECATED_ADAPTER_IDS))
