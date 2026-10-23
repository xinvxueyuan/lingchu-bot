"""WebUI 旧兼容端点（deprecated）。

改造后 WebUI 由 oRPC 过程（`services/webui/orpc.py`）提供全部数据能力。本模块
只保留改造前已对外暴露的三个轻量端点，供仍按旧路径访问的客户端过渡：

- `{legacy_root}/status`
- `{legacy_root}/info`
- `{legacy_root}/verify-password`

其余 OneBot 只读透传端点（login-info / status / version-info / groups / friends、
tools/cookies、tools/csrf_token、qq/nickname）已由对应的 oRPC 过程取代并删除。

**路径全部由 `build_webui_urls` 派生**，不硬编码前缀，保证
`LINGCHU_WEBUI_BASE_PATH` 改动后旧端点也随之迁移。

鉴权说明：改造后浏览器只携带 HttpOnly 会话 Cookie，不再支持在请求头或查询参数里
传口令。因此兼容端点同样只认 Cookie 会话；`verify-password` 例外——它本身就是
登录用的口令校验入口，直接比对请求体。
"""

from __future__ import annotations

import hmac
from typing import TYPE_CHECKING, Any

from starlette.requests import Request
from starlette.responses import JSONResponse

from ...core.config import plugin_config
from ...core.webui_session import WEBUI_SESSION_COOKIE, verify_session

if TYPE_CHECKING:
    from .paths import WebuiUrls


def _unauthorized() -> JSONResponse:
    """构造 401 未授权响应。

    Returns:
        JSONResponse: `{"detail": "unauthorized"}`。

    """
    return JSONResponse(status_code=401, content={"detail": "unauthorized"})


def verify_webui_password(request: Request) -> bool:
    """校验请求是否持有有效的 WebUI 会话。

    配置为空字符串时一律拒绝（fail-closed）：未设置口令即视为未启用 WebUI。

    Args:
        request: 当前请求。

    Returns:
        bool: 会话有效返回 True。

    """
    expected = str(plugin_config.lingchu_webui_password)
    if not expected:
        return False
    token = request.cookies.get(WEBUI_SESSION_COOKIE)
    return verify_session(expected, token) is not None


async def webui_verify_password_endpoint(request: Request) -> JSONResponse:
    """口令校验端点：对比请求体中的密码与配置值。

    期望密钥未配置时拒绝一切登录，避免空密钥放行。

    Args:
        request: 携带 `{"password": "..."}` 的请求。

    Returns:
        JSONResponse: 校验通过返回 `{"ok": true}`，否则 401。

    """
    expected = str(plugin_config.lingchu_webui_password)
    if not expected:
        return _unauthorized()
    try:
        payload: Any = await request.json()
    except Exception:
        payload = {}
    provided = payload.get("password") if isinstance(payload, dict) else None
    if not isinstance(provided, str) or not hmac.compare_digest(provided, expected):
        return _unauthorized()
    return JSONResponse(content={"ok": True})


async def webui_status_endpoint(request: Request) -> JSONResponse:
    """只读端点：返回 bot 基本状态。

    Args:
        request: 当前请求。

    Returns:
        JSONResponse: `{"status", "plugin", "version"}` 或 401。

    """
    if not verify_webui_password(request):
        return _unauthorized()
    return JSONResponse({
        "status": "ok",
        "plugin": "lingchu-bot",
        "version": plugin_config.core_version,
    })


async def webui_info_endpoint(request: Request) -> JSONResponse:
    """只读端点：返回插件基本信息。

    Args:
        request: 当前请求。

    Returns:
        JSONResponse: `{"name", "description", "version"}` 或 401。

    """
    if not verify_webui_password(request):
        return _unauthorized()
    return JSONResponse({
        "name": "lingchu-bot",
        "description": "跨平台群组管理机器人",
        "version": plugin_config.core_version,
    })


def build_legacy_routes(
    urls: WebuiUrls,
) -> tuple[tuple[str, Any, list[str]], ...]:
    """构造旧兼容端点路由。

    Args:
        urls: 由 base path 派生的路径集合。

    Returns:
        tuple: Starlette `add_route` 参数三元组序列。

    """
    return (
        (f"{urls.legacy_root}/status", webui_status_endpoint, ["GET"]),
        (f"{urls.legacy_root}/info", webui_info_endpoint, ["GET"]),
        (
            f"{urls.legacy_root}/verify-password",
            webui_verify_password_endpoint,
            ["POST"],
        ),
    )


__all__ = [
    "build_legacy_routes",
    "verify_webui_password",
    "webui_info_endpoint",
    "webui_status_endpoint",
    "webui_verify_password_endpoint",
]
