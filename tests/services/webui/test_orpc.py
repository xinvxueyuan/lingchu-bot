"""`services/webui/orpc.py` 的测试：14 条 oRPC 过程的响应契约与路由注册。

约定（与实现一致）：
- 成功 `{"json": ...}`；业务错误 `{"error": {"code", ...}}` 且 HTTP 200；
- 鉴权失败 401；输入非法 400；
- 静态挂载必须先于本模块路由**之后**注册（本文件只验证路由本身）。

实现细节：用 `httpx.AsyncClient + ASGITransport` 驱动最小 Starlette 应用，
不使用 `starlette.testclient.TestClient` —— 后者会触发
`StarletteDeprecationWarning`，而项目的 `filterwarnings = ["error", ...]`
会把它升级为失败。
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager
import json
from typing import Any, cast

import httpx
from httpx import ASGITransport, AsyncClient
import pytest
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

from src.plugins.nonebot_plugin_lingchu_bot.services.webui import orpc
from src.plugins.nonebot_plugin_lingchu_bot.services.webui.paths import (
    build_webui_urls,
)

_PASSWORD = "open sesame"
_COOKIE_NAME = "lingchu_webui_session"


def _build_app(cookies: dict[str, str] | None = None) -> AsyncClient:
    """构造只注册 oRPC 路由的最小应用，并返回绑定它的客户端。

    Args:
        cookies: 客户端默认携带的 Cookie（用于已登录场景）。

    Returns:
        AsyncClient: 指向该应用的异步客户端。

    """
    urls = build_webui_urls()
    app = Starlette(
        routes=[
            Route(path, endpoint, methods=methods)
            for path, endpoint, methods in orpc.build_procedure_routes(urls)
        ]
    )
    app.state.webui_urls = urls
    transport = ASGITransport(app=cast("Any", app))
    return AsyncClient(
        transport=transport,
        base_url="http://webui.test",
        cookies=cookies,
    )


@pytest.fixture
def configured(monkeypatch: pytest.MonkeyPatch) -> Iterator[str]:
    """把 `orpc._session_password` 固定为已配置口令。"""
    monkeypatch.setattr(orpc, "_session_password", lambda: _PASSWORD)
    yield _PASSWORD


@pytest.fixture
def unconfigured(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """把 `orpc._session_password` 固定为空（未启用 WebUI）。"""
    monkeypatch.setattr(orpc, "_session_password", lambda: "")
    yield None


def _url(path: str) -> str:
    return build_webui_urls().rpc(path)


async def _login_and_get_cookie(client: AsyncClient) -> str:
    """登录并返回会话 Cookie 值。

    Args:
        client: 已绑定应用的客户端。

    Returns:
        str: Cookie 值。

    """
    response = await client.post(_url("/auth/login"), json={"password": _PASSWORD})
    assert response.status_code == 200
    return str(response.cookies[_COOKIE_NAME])


@asynccontextmanager
async def _signed_in_app() -> AsyncIterator[AsyncClient]:
    """已完成登录、携带会话 Cookie 的客户端。

    先登录拿到 Cookie，再用 `client.cookies` 新建客户端 —— httpx 0.28 对
    "逐请求传入 cookies=" 发出 DeprecationWarning，而项目把警告配置为 error。

    Yields:
        AsyncClient: 携带有效会话 Cookie 的客户端。

    """
    urls = build_webui_urls()
    app = Starlette(
        routes=[
            Route(path, endpoint, methods=methods)
            for path, endpoint, methods in orpc.build_procedure_routes(urls)
        ]
    )
    app.state.webui_urls = urls
    transport = ASGITransport(app=cast("Any", app))

    async with AsyncClient(
        transport=transport, base_url="http://webui.test"
    ) as anonymous:
        await _login_and_get_cookie(anonymous)
        cookies = httpx.Cookies(anonymous.cookies)
    async with AsyncClient(
        transport=transport, base_url="http://webui.test", cookies=cookies
    ) as signed_in:
        yield signed_in


# --- auth/login -------------------------------------------------------------


async def test_login_missing_password_returns_400(configured: str) -> None:
    assert configured
    async with _build_app() as client:
        response = await client.post(_url("/auth/login"), json={})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "bad_request"


async def test_login_non_json_body_returns_400(configured: str) -> None:
    assert configured
    async with _build_app() as client:
        response = await client.post(
            _url("/auth/login"),
            content=b"not-json",
            headers={"content-type": "application/json"},
        )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "bad_request"


async def test_login_wrong_password_returns_401(configured: str) -> None:
    assert configured
    async with _build_app() as client:
        response = await client.post(
            _url("/auth/login"), json={"password": "not-the-password"}
        )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_password"
    assert _COOKIE_NAME not in response.cookies


async def test_login_success_sets_hardened_cookie(configured: str) -> None:
    assert configured
    async with _build_app() as client:
        response = await client.post(_url("/auth/login"), json={"password": _PASSWORD})

    assert response.status_code == 200
    body = response.json()
    assert body["json"]["ok"] is True
    assert isinstance(body["json"]["expiresAt"], int)

    set_cookie = response.headers["set-cookie"]
    assert _COOKIE_NAME in set_cookie
    assert "HttpOnly" in set_cookie
    assert f"Path={build_webui_urls().cookie_path}" in set_cookie
    assert "Path=/lc/webui" in set_cookie
    assert "SameSite=lax" in set_cookie.lower().replace("samesite=lax", "SameSite=lax")


async def test_login_when_password_not_configured(unconfigured: None) -> None:
    assert unconfigured is None
    async with _build_app() as client:
        response = await client.post(_url("/auth/login"), json={"password": "anything"})
    assert response.status_code == 200
    assert response.json()["error"]["code"] == "password_not_configured"
    assert _COOKIE_NAME not in response.cookies


# --- auth/me ----------------------------------------------------------------


async def test_me_without_cookie_returns_401(configured: str) -> None:
    assert configured
    async with _build_app() as client:
        response = await client.get(_url("/auth/me"))
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


async def test_me_with_valid_session(configured: str) -> None:
    assert configured
    async with _signed_in_app() as client:
        response = await client.get(_url("/auth/me"))
    assert response.status_code == 200
    body = response.json()["json"]
    assert body["sub"] == "root"
    assert isinstance(body["expiresAt"], int)


async def test_me_with_forged_cookie_returns_401(configured: str) -> None:
    assert configured
    async with _build_app(cookies={_COOKIE_NAME: "forged.value"}) as client:
        response = await client.get(_url("/auth/me"))
    assert response.status_code == 401


# --- auth/logout ------------------------------------------------------------


async def test_logout_clears_cookie(configured: str) -> None:
    assert configured
    async with _signed_in_app() as client:
        response = await client.post(_url("/auth/logout"))
    assert response.status_code == 200
    assert response.json()["json"]["ok"] is True
    set_cookie = response.headers["set-cookie"]
    assert _COOKIE_NAME in set_cookie
    assert f"Path={build_webui_urls().cookie_path}" in set_cookie


# --- overview ---------------------------------------------------------------


async def test_overview_requires_session(configured: str) -> None:
    assert configured
    async with _build_app() as client:
        response = await client.get(_url("/overview"))
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


async def test_overview_reports_onebot_disconnected(
    configured: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert configured
    bot_error = RuntimeError("no bot connected")

    def _no_bot() -> Any:
        raise bot_error

    monkeypatch.setattr(orpc, "get_bot", _no_bot)

    async with _signed_in_app() as client:
        response = await client.get(_url("/overview"))

    assert response.status_code == 200
    payload = response.json()["json"]
    assert set(payload["errors"]) == {
        "loginInfo",
        "status",
        "versionInfo",
        "groups",
        "friends",
    }
    assert set(payload["errors"].values()) == {"onebot_disconnected"}
    assert "lingchuVersion" in payload
    # 五块全部失败时不应产出任何数据块。
    for block in ("loginInfo", "status", "versionInfo", "groups", "friends"):
        assert block not in payload


# --- onebot/stranger --------------------------------------------------------


@pytest.mark.parametrize("qq", ["abc", "123", "12ab", "", "1" * 16, "-12345"])
async def test_stranger_rejects_invalid_qq(configured: str, qq: str) -> None:
    assert configured
    async with _signed_in_app() as client:
        response = await client.get(
            _url("/onebot/stranger"), params=_orpc_query({"qq": qq})
        )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_qq"


async def test_stranger_returns_nickname(
    configured: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert configured
    calls: list[tuple[str, dict[str, Any]]] = []

    async def _fake_call(api: str, **data: Any) -> Any:
        calls.append((api, data))
        return {"user_id": 123, "nickname": "群友甲"}

    monkeypatch.setattr(orpc, "_call_onebot", _fake_call)

    async with _signed_in_app() as client:
        response = await client.get(
            _url("/onebot/stranger"), params=_orpc_query({"qq": "1234"})
        )

    assert response.status_code == 200, response.text
    assert response.json()["json"] == {"qq": "1234", "nickname": "群友甲"}
    assert calls == [("get_stranger_info", {"user_id": 1234})]


async def test_stranger_not_found(
    configured: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert configured

    async def _fake_call(api: str, **data: Any) -> Any:
        _ = api, data
        return {}

    monkeypatch.setattr(orpc, "_call_onebot", _fake_call)

    async with _signed_in_app() as client:
        response = await client.get(
            _url("/onebot/stranger"), params=_orpc_query({"qq": "1234"})
        )

    assert response.status_code == 200, response.text
    error = response.json()["error"]
    assert error["code"] == "not_found"
    assert "json" not in response.json()


# --- 路由注册 ---------------------------------------------------------------


def _orpc_query(payload: dict[str, Any]) -> dict[str, str]:
    """把过程入参编码成 oRPC GET 传输使用的 `?data=<json>` 查询参数。

    Args:
        payload: 过程入参。

    Returns:
        dict[str, str]: 可直接传给 httpx 的 params。
    """
    return {"data": json.dumps({"json": payload})}


def test_build_procedure_routes_shape() -> None:
    urls = build_webui_urls()
    routes = orpc.build_procedure_routes(urls)

    assert isinstance(routes, tuple)
    assert len(routes) == 14
    paths = [path for path, _, _ in routes]
    assert len(set(paths)) == 14
    for path in paths:
        assert path.startswith(urls.rpc_root)
    for _, _endpoint, methods in routes:
        assert methods
        assert all(method in {"GET", "POST"} for method in methods)


def test_procedure_routes_use_custom_base() -> None:
    urls = build_webui_urls("/assets/lc/ui")
    routes = orpc.build_procedure_routes(urls)
    assert all(path.startswith("/assets/lc/ui/v1/rpc") for path, _, _ in routes)
    assert urls.rpc("/auth/login") in {path for path, _, _ in routes}


# --- 方法约束 ---------------------------------------------------------------


async def test_login_method_envelope(configured: str) -> None:
    """含 oRPC 两种传输信封的登录请求都必须成功。

    RPC 传输对 POST 用 body 信封、对 GET 用 `?data=` 信封；两种方法都必须被接受
    且解析结果一致——前端按契约切换 method 时不会 405。
    """
    assert configured
    async with _build_app() as client:
        via_post = await client.post(
            _url("/auth/login"), json={"json": {"password": configured}}
        )
        via_get = await client.get(
            _url("/auth/login"), params=_orpc_query({"password": configured})
        )
    assert via_post.status_code == 200
    assert via_get.status_code == 200
    assert via_post.json()["json"]["ok"] is True
    assert via_get.json()["json"]["ok"] is True


async def test_orpc_routes_win_over_catch_all_mount(configured: str) -> None:
    """ORPC 路由先注册时，不会被 `{base}/` 的 catch-all Mount 吞成 HTML。"""
    assert configured
    urls = build_webui_urls()
    app = Starlette(
        routes=[
            Route(path, endpoint, methods=methods)
            for path, endpoint, methods in orpc.build_procedure_routes(urls)
        ]
    )
    app.state.webui_urls = urls

    async def _catch_all(request: Request) -> JSONResponse:
        _ = request
        return JSONResponse({"json": "swallowed"})

    app.router.routes.append(
        Mount(urls.base, routes=[Route("/{rest:path}", _catch_all)])
    )

    async with AsyncClient(
        transport=ASGITransport(app=cast("Any", app)),
        base_url="http://webui.test",
    ) as client:
        response = await client.get(_url("/auth/me"))

    # 未带 Cookie → oRPC 的 401，而不是 catch-all 的 {"json": "swallowed"}。
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"
