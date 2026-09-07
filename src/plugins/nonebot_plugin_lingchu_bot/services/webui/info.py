"""WebUI 动态运行时端点逻辑（nonebot 侧）。

提供只读端点所需的核心逻辑、简易字符串密码校验，以及登录密码校验端点。
绝不实现任何 JWT 签发或令牌功能。本模块不依赖驱动器，可在不启动 NoneBot 的情况下导入。
"""

from __future__ import annotations

import hmac
from typing import Any

from nonebot import get_bot
from starlette.requests import Request
from starlette.responses import JSONResponse

from ...core.config import plugin_config

# 请求头与查询参数名（二选一携带密码）
_WEBUI_PASSWORD_HEADER: str = "X-Lingchu-Webui-Password"
_WEBUI_PASSWORD_QUERY: str = "webui_password"

# 路由路径
WEBUI_STATUS_PATH: str = "/lingchu-bot/webui/v1/status"
WEBUI_INFO_PATH: str = "/lingchu-bot/webui/v1/info"
WEBUI_VERIFY_PASSWORD_PATH: str = "/lingchu-bot/webui/v1/verify-password"


def verify_webui_password(request: Request) -> bool:
    """校验 WebUI 简易字符串密码。

    配置为空字符串时直接放行（默认无鉴权）；非空时严格比较请求携带的密码。
    使用恒定时间比较避免计时侧信道。

    Args:
        request: Starlette 请求对象，从中读取密码头或查询参数。

    Returns:
        bool: 密码校验通过返回 True，否则返回 False。

    """
    expected = str(plugin_config.lingchu_webui_password)
    if not expected:
        return True
    provided = request.headers.get(_WEBUI_PASSWORD_HEADER)
    if provided is None:
        provided = request.query_params.get(_WEBUI_PASSWORD_QUERY)
    if provided is None:
        return False
    return hmac.compare_digest(provided, expected)


def _unauthorized() -> JSONResponse:
    """构造 401 未授权响应。"""
    return JSONResponse(status_code=401, content={"detail": "unauthorized"})


async def webui_verify_password_endpoint(request: Request) -> JSONResponse:
    """登录密码校验端点：对比前端传递的密码与 .env 中配置的唯一密钥。

    这是三个系统（前端 → WebUI 后端 → nonebot 端点）之间的唯一密钥校验入口。
    期望密钥未配置时拒绝一切登录，避免空密钥放行。
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
    """只读端点：返回 bot 基本状态 JSON。"""
    if not verify_webui_password(request):
        return _unauthorized()
    return JSONResponse({
        "status": "ok",
        "plugin": "lingchu-bot",
        "version": plugin_config.core_version,
    })


async def webui_info_endpoint(request: Request) -> JSONResponse:
    """只读端点：返回插件基本信息 JSON。"""
    if not verify_webui_password(request):
        return _unauthorized()
    return JSONResponse({
        "name": "lingchu-bot",
        "description": "跨平台群组管理机器人",
        "version": plugin_config.core_version,
    })


WEBUI_QQ_NICKNAME_PATH: str = "/lingchu-bot/webui/v1/qq/nickname/{qq}"

WEBUI_TOOLS_COOKIES_PATH: str = "/lingchu-bot/webui/v1/tools/cookies"
WEBUI_TOOLS_CSRF_TOKEN_PATH: str = "/lingchu-bot/webui/v1/tools/csrf_token"

# OneBot 只读透传端点（统一走 _call_api_proxy 鉴权与异常处理）
WEBUI_ONEBOT_LOGIN_INFO_PATH: str = "/lingchu-bot/webui/v1/onebot/login-info"
WEBUI_ONEBOT_STATUS_PATH: str = "/lingchu-bot/webui/v1/onebot/status"
WEBUI_ONEBOT_VERSION_INFO_PATH: str = "/lingchu-bot/webui/v1/onebot/version-info"
WEBUI_ONEBOT_GROUPS_PATH: str = "/lingchu-bot/webui/v1/onebot/groups"
WEBUI_ONEBOT_FRIENDS_PATH: str = "/lingchu-bot/webui/v1/onebot/friends"


async def webui_qq_nickname_endpoint(request: Request, qq: str) -> JSONResponse:
    """WebUI 端点：用 OneBot get_stranger_info 返回 nick_name（仅简单调用，不加工）。"""
    if not verify_webui_password(request):
        return _unauthorized()
    if not (qq.isdigit() and 4 <= len(qq) <= 15):
        return JSONResponse(status_code=400, content={"detail": "invalid_qq"})
    try:
        bot = get_bot()
        info = await bot.call_api("get_stranger_info", user_id=int(qq))
    except Exception:
        return JSONResponse(status_code=404, content={"detail": "not_found"})
    if not isinstance(info, dict) or not info.get("nickname"):
        return JSONResponse(status_code=404, content={"detail": "not_found"})
    return JSONResponse(content={"qq": qq, "nickname": info["nickname"]})


async def _call_api_proxy(request: Request, api: str, **data: object) -> JSONResponse:
    """轻量透传：校验密码后直接调用 OneBot API 并回传结果，不做加工。"""
    if not verify_webui_password(request):
        return _unauthorized()
    try:
        bot = get_bot()
    except Exception:
        # 后端已运行但未连接任何 OneBot11 协议端：返回语义化错误码供上层边界守卫识别。
        return JSONResponse(
            status_code=502,
            content={"detail": "onebot_disconnected"},
        )
    try:
        result = await bot.call_api(api, **data)
    except Exception as exc:
        return JSONResponse(
            status_code=502,
            content={"detail": "upstream_error", "message": str(exc)},
        )
    return JSONResponse(content={"result": result})


async def webui_tools_cookies_endpoint(request: Request) -> JSONResponse:
    """轻量工具：透传 OneBot get_cookies（可选 domain 查询参数）。"""
    domain = request.query_params.get("domain")
    return await _call_api_proxy(
        request, "get_cookies", **({"domain": domain} if domain else {})
    )


async def webui_tools_csrf_token_endpoint(request: Request) -> JSONResponse:
    """轻量工具：透传 OneBot get_csrf_token。"""
    return await _call_api_proxy(request, "get_csrf_token")


async def webui_onebot_login_info_endpoint(request: Request) -> JSONResponse:
    """轻量工具：透传 OneBot get_login_info。"""
    return await _call_api_proxy(request, "get_login_info")


async def webui_onebot_status_endpoint(request: Request) -> JSONResponse:
    """轻量工具：透传 OneBot get_status。"""
    return await _call_api_proxy(request, "get_status")


async def webui_onebot_version_info_endpoint(request: Request) -> JSONResponse:
    """轻量工具：透传 OneBot get_version_info。"""
    return await _call_api_proxy(request, "get_version_info")


async def webui_onebot_groups_endpoint(request: Request) -> JSONResponse:
    """轻量工具：透传 OneBot get_group_list。"""
    return await _call_api_proxy(request, "get_group_list")


async def webui_onebot_friends_endpoint(request: Request) -> JSONResponse:
    """轻量工具：透传 OneBot get_friend_list。"""
    return await _call_api_proxy(request, "get_friend_list")
