"""「启动WebUI」handle 的默认配置。

WebUI 由 NoneBot 同进程托管且挂载幂等，没有可调默认字段；这里注册一份空
`defaults`，让 `HandleConfigManager` 能读写 `webui_start.toml`。
"""

from __future__ import annotations

from typing import Any

from . import register_handle_defaults


def _webui_start_defaults() -> dict[str, Any]:
    """返回「启动WebUI」的默认配置。

    Returns:
        dict[str, Any]: 启用状态、空默认值表与空策略表。

    """
    return {"enabled": True, "defaults": {}, "policies": {}}


register_handle_defaults("webui_start", _webui_start_defaults)
