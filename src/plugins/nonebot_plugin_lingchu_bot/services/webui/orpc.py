"""WebUI oRPC 服务端：类型化过程路由。

改造前是"前端 → Node 后端 → NoneBot"三层结构，其中 Node 侧做了 JWT 签发、
口令内存缓存、`/api/overview` 聚合与 `/api/*` 反向代理。改造后 Node 层整体消失，
本模块直接在同进程内实现同一批过程：

- 所有过程都是**只读**的（现有后端 100% 是 OneBot 只读透传 + 插件自产信息）；
- 响应沿用 oRPC 的封装约定：成功 `{"json": ...}`，业务错误
  `{"error": {"code", "message}}` 且 HTTP 200；仅**鉴权失败**保持
  HTTP 401，便于前端用统一拦截器跳登录页；
- 输入校验失败返回 400 `{"error": {"code": "bad_request"}}`。

路径前缀全部来自 `paths.build_webui_urls`，本模块不硬编码任何 URL。
"""

from __future__ import annotations

import asyncio
import hmac
import json
from typing import TYPE_CHECKING, Any, cast

from nonebot import get_bot, logger
from starlette.requests import Request
from starlette.responses import JSONResponse

from ...core.config import plugin_config
from ...core.webui_session import (
    DEFAULT_SESSION_TTL_SECONDS,
    issue_session,
    verify_session,
)

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from .paths import WebuiUrls

# 会话 Cookie 名（与 core.webui_session 保持一致，此处仅用于读写 header）。
_SESSION_COOKIE: str = "lingchu_webui_session"

# oRPC 的 RPC 传输会按契约声明的 method 选择 GET/POST；两条都接受，
# 前端改用任一方法都不会收到 405（入参统一由 _read_input 解包）。
_ANY_METHOD: list[str] = ["GET", "POST"]

# QQ 号合法形态：4~15 位数字。
_QQ_ID_MAX_LENGTH: int = 15
_QQ_ID_MIN_LENGTH: int = 4


def _error(code: str, message: str = "", *, status: int = 200) -> JSONResponse:
    """构造 oRPC 错误响应。

    Args:
        code: 机器可读错误码。
        message: 人类可读补充说明（可为空）。
        status: HTTP 状态码；业务错误用 200，鉴权失败用 401，输入非法用 400。

    Returns:
        JSONResponse: 封装后的错误响应。

    """
    payload: dict[str, Any] = {"code": code}
    if message:
        payload["message"] = message
    return JSONResponse(status_code=status, content={"error": payload})


def _ok(value: Any) -> JSONResponse:
    """构造 oRPC 成功响应。

    Args:
        value: 可 JSON 序列化的业务返回值。

    Returns:
        JSONResponse: `{"json": value}`。

    """
    return JSONResponse(content={"json": value})


async def _read_input(request: Request) -> dict[str, Any]:
    """从 oRPC 请求中取出过程入参。

    oRPC 的 RPC 传输把入参包在 `{"json": <input>}` 信封里，并按方法放在不同位置：

    - `POST`：JSON body，形如 `{"json": {"password": "..."}}`；
    - `GET`：URL 编码的 `?data={"json": {...}}`。

    两种形态都接受，缺失或非法时返回空字典（由各过程自行判定必填项）。

    Args:
        request: 当前请求。

    Returns:
        dict[str, Any]: 解包后的入参。

    """
    payload: Any = {}
    if request.method.upper() == "POST":
        try:
            payload = await request.json()
        except Exception:
            # 空体 / 非法 JSON 统一按「无入参」处理，由各过程自行判定必填项。
            payload = {}
    else:
        raw = request.query_params.get("data")
        if raw:
            try:
                payload = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                payload = {}

    if isinstance(payload, dict):
        inner = payload.get("json")
        if isinstance(inner, dict):
            return inner
        return payload
    return {}


def _session_password() -> str:
    """读取当前配置的 WebUI 登录口令。

    Returns:
        str: 配置值；未配置时为空字符串（调用方据此 fail-closed）。

    """
    return str(plugin_config.lingchu_webui_password)


def _session_ttl() -> int:
    """读取会话有效期配置。

    Returns:
        int: 秒数；缺失或非法时回退默认值。

    """
    value = getattr(plugin_config, "lingchu_webui_session_ttl", None)
    if not isinstance(value, int):
        return DEFAULT_SESSION_TTL_SECONDS
    return value if value > 0 else DEFAULT_SESSION_TTL_SECONDS


def _require_session(request: Request) -> JSONResponse | None:
    """校验会话 Cookie。

    Args:
        request: 当前请求。

    Returns:
        JSONResponse | None: 未通过时返回 401 响应；通过时返回 None。

    """
    token = request.cookies.get(_SESSION_COOKIE)
    if verify_session(_session_password(), token) is None:
        return _error("unauthorized", "会话无效或已过期", status=401)
    return None


async def _call_onebot(api: str, **data: Any) -> Any:
    """调用 OneBot API 并返回原始结果。

    无可用 bot 时抛 `RuntimeError("onebot_disconnected")`，上游失败时抛
    `RuntimeError("upstream_error")`；调用方据此映射为 oRPC 错误码。

    Args:
        api: OneBot API 名。
        **data: 传给 API 的参数。

    Returns:
        Any: 上游返回结果。

    Raises:
        RuntimeError: 没有已连接的 bot，或上游调用失败。

    """
    try:
        bot = get_bot()
    except Exception as exc:
        logger.debug("WebUI 取 bot 失败: {!r}", exc)
        raise RuntimeError("onebot_disconnected") from exc
    try:
        return await bot.call_api(api, **data)
    except Exception as exc:
        logger.debug("WebUI 上游调用失败: api={} error={!r}", api, exc)
        raise RuntimeError("upstream_error") from exc


def _failure_code(exc: BaseException) -> str:
    """把上游异常映射为 oRPC 错误码。

    Args:
        exc: 捕获到的异常。

    Returns:
        str: `onebot_disconnected` / `upstream_error`。

    """
    args = getattr(exc, "args", ())
    if args and args[0] == "onebot_disconnected":
        return "onebot_disconnected"
    return "upstream_error"


async def _aggregate_overview() -> dict[str, Any]:
    """并发聚合概览数据，单块失败不影响其它块。

    Returns:
        dict[str, Any]: 概览载荷；失败的块在 `errors` 里记录错误码。

    """

    async def safe(api: str) -> Any:
        return await _call_onebot(api)

    results = await asyncio.gather(
        safe("get_login_info"),
        safe("get_status"),
        safe("get_version_info"),
        safe("get_group_list"),
        safe("get_friend_list"),
        return_exceptions=True,
    )

    data: dict[str, Any] = {"errors": {}}
    errors: dict[str, str] = cast("dict[str, str]", data["errors"])
    blocks = ("loginInfo", "status", "versionInfo", "groups", "friends")
    for key, value in zip(blocks, results, strict=True):
        if isinstance(value, BaseException):
            errors[key] = (
                "onebot_disconnected"
                if _failure_code(value) == "onebot_disconnected"
                else "unavailable"
            )
        else:
            data[key] = value

    data["lingchuVersion"] = str(plugin_config.core_version)
    return data


async def handle_login(request: Request) -> JSONResponse:
    """`auth/login`：用唯一口令换取会话 Cookie。

    Args:
        request: 携带 `{"password": "..."}` 的 JSON 请求。

    Returns:
        JSONResponse: 成功 `{"json": {"ok": true, "expiresAt": ...}}`；
            口令为空（未启用）返回业务错误；口令错误返回 401。

    """
    password = _session_password()
    if not password:
        return _error(
            "password_not_configured",
            "未配置 LINGCHU_WEBUI_PASSWORD，WebUI 登录已禁用",
        )
    provided = (await _read_input(request)).get("password")
    if not isinstance(provided, str):
        return _error("bad_request", "缺少 password 字段", status=400)
    if not hmac.compare_digest(provided, password):
        return _error("invalid_password", "口令错误", status=401)

    ttl = _session_ttl()
    token, expires_at = issue_session(password, ttl_seconds=ttl)
    response = _ok({"ok": True, "expiresAt": expires_at})
    response.set_cookie(
        _SESSION_COOKIE,
        token,
        max_age=ttl,
        path=request.app.state.webui_urls.cookie_path,
        httponly=True,
        samesite="lax",
    )
    return response


async def handle_logout(request: Request) -> JSONResponse:
    """`auth/logout`：清除会话 Cookie。

    无状态会话没有服务端吊销表，登出即删除 Cookie；即使 Cookie 曾被窃取，
    其有效期仍由 `expiresAt` 与进程 nonce 共同限制。

    Args:
        request: 当前请求。

    Returns:
        JSONResponse: `{"json": {"ok": true}}`。

    """
    response = _ok({"ok": True})
    response.delete_cookie(
        _SESSION_COOKIE,
        path=request.app.state.webui_urls.cookie_path,
    )
    return response


async def handle_me(request: Request) -> JSONResponse:
    """`auth/me`：返回当前会话信息。

    Args:
        request: 当前请求。

    Returns:
        JSONResponse: 合法会话返回 `{"json": {"sub", "expiresAt"}}`，否则 401。

    """
    token = request.cookies.get(_SESSION_COOKIE)
    claims = verify_session(_session_password(), token)
    if claims is None:
        return _error("unauthorized", "会话无效或已过期", status=401)
    return _ok({"sub": claims.sub, "expiresAt": claims.expires_at})


async def handle_overview(request: Request) -> JSONResponse:
    """`overview`：一次性返回概览数据。

    Args:
        request: 当前请求。

    Returns:
        JSONResponse: 概览载荷，或 401。

    """
    unauthorized = _require_session(request)
    if unauthorized is not None:
        return unauthorized
    return _ok(await _aggregate_overview())


def _make_onebot_handler(api: str) -> Callable[[Request], Awaitable[JSONResponse]]:
    """生成一个 OneBot 只读透传过程。

    Args:
        api: OneBot API 名。

    Returns:
        Callable: Starlette 端点。

    """

    async def handler(request: Request) -> JSONResponse:
        unauthorized = _require_session(request)
        if unauthorized is not None:
            return unauthorized
        try:
            value = await _call_onebot(api)
        except RuntimeError as exc:
            return _error(_failure_code(exc), "上游调用失败")
        return _ok(value)

    handler.__name__ = f"handle_{api}"
    return handler


async def handle_stranger(request: Request) -> JSONResponse:
    """`onebot/stranger`：按 QQ 号取昵称。

    Args:
        request: 携带 `?qq=` 的请求。

    Returns:
        JSONResponse: `{"json": {"qq", "nickname"}}`；QQ 非法 400，查不到 404。

    """
    unauthorized = _require_session(request)
    if unauthorized is not None:
        return unauthorized
    qq = str((await _read_input(request)).get("qq", ""))
    if not (qq.isdigit() and _QQ_ID_MIN_LENGTH <= len(qq) <= _QQ_ID_MAX_LENGTH):
        return _error("invalid_qq", "QQ 号格式非法", status=400)
    try:
        info = await _call_onebot("get_stranger_info", user_id=int(qq))
    except RuntimeError as exc:
        return _error(_failure_code(exc), "上游调用失败")
    nickname = info.get("nickname") if isinstance(info, dict) else None
    if not nickname:
        return _error("not_found", "未找到该用户")
    return _ok({"qq": qq, "nickname": nickname})


async def handle_cookies(request: Request) -> JSONResponse:
    """`onebot/cookies`：透传 `get_cookies`（可选 domain）。

    Args:
        request: 当前请求。

    Returns:
        JSONResponse: 上游结果。

    """
    unauthorized = _require_session(request)
    if unauthorized is not None:
        return unauthorized
    domain = (await _read_input(request)).get("domain")
    params: dict[str, Any] = {"domain": domain} if domain else {}
    try:
        value = await _call_onebot("get_cookies", **params)
    except RuntimeError as exc:
        return _error(_failure_code(exc), "上游调用失败")
    return _ok(value)


async def handle_csrf_token(request: Request) -> JSONResponse:
    """`onebot/csrf-token`：透传 `get_csrf_token`。

    Args:
        request: 当前请求。

    Returns:
        JSONResponse: 上游结果。

    """
    unauthorized = _require_session(request)
    if unauthorized is not None:
        return unauthorized
    try:
        value = await _call_onebot("get_csrf_token")
    except RuntimeError as exc:
        return _error(_failure_code(exc), "上游调用失败")
    return _ok(value)


async def handle_system_status(request: Request) -> JSONResponse:
    """`system/status`：插件自产状态。

    Args:
        request: 当前请求。

    Returns:
        JSONResponse: `{"status","plugin","version"}`。

    """
    unauthorized = _require_session(request)
    if unauthorized is not None:
        return unauthorized
    return _ok({
        "status": "ok",
        "plugin": "lingchu-bot",
        "version": plugin_config.core_version,
    })


async def handle_system_info(request: Request) -> JSONResponse:
    """`system/info`：插件自产基本信息。

    Args:
        request: 当前请求。

    Returns:
        JSONResponse: `{"name","description","version"}`。

    """
    unauthorized = _require_session(request)
    if unauthorized is not None:
        return unauthorized
    return _ok({
        "name": "lingchu-bot",
        "description": "跨平台群组管理机器人",
        "version": plugin_config.core_version,
    })


def build_procedure_routes(
    urls: WebuiUrls,
) -> tuple[tuple[str, Callable[[Request], Awaitable[JSONResponse]], list[str]], ...]:
    """构造全部 oRPC 路由（路径, 端点, 方法）。

    顺序即注册顺序，调用方必须先注册本函数返回的路由，再挂载静态应用，
    否则 SPA fallback 会把所有 RPC 请求吞成 `index.html`。

    Args:
        urls: 由 base path 派生的路径集合。

    Returns:
        tuple: Starlette `add_route` 参数三元组序列。

    """
    routes: list[
        tuple[str, Callable[[Request], Awaitable[JSONResponse]], list[str]]
    ] = [
        (urls.rpc("/auth/login"), handle_login, _ANY_METHOD),
        (urls.rpc("/auth/logout"), handle_logout, _ANY_METHOD),
        (urls.rpc("/auth/me"), handle_me, _ANY_METHOD),
        (urls.rpc("/overview"), handle_overview, _ANY_METHOD),
        (
            urls.rpc("/onebot/login-info"),
            _make_onebot_handler("get_login_info"),
            _ANY_METHOD,
        ),
        (urls.rpc("/onebot/status"), _make_onebot_handler("get_status"), _ANY_METHOD),
        (
            urls.rpc("/onebot/version-info"),
            _make_onebot_handler("get_version_info"),
            _ANY_METHOD,
        ),
        (
            urls.rpc("/onebot/groups"),
            _make_onebot_handler("get_group_list"),
            _ANY_METHOD,
        ),
        (
            urls.rpc("/onebot/friends"),
            _make_onebot_handler("get_friend_list"),
            _ANY_METHOD,
        ),
        (urls.rpc("/onebot/stranger"), handle_stranger, _ANY_METHOD),
        (urls.rpc("/onebot/cookies"), handle_cookies, _ANY_METHOD),
        (urls.rpc("/onebot/csrf-token"), handle_csrf_token, _ANY_METHOD),
        (urls.rpc("/system/status"), handle_system_status, _ANY_METHOD),
        (urls.rpc("/system/info"), handle_system_info, _ANY_METHOD),
    ]
    return tuple(routes)
