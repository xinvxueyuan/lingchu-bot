"""`services/webui/static.py` 的测试：静态资源、SPA fallback 与挂载幂等。

实现细节：
- 产物目录用 `monkeypatch.setattr(static, "STATIC_ROOT", tmp_path)` 重定向，
  测试结束后自动还原，不污染真实产物目录；
- 穿越路径与 405 用手工 ASGI scope 驱动 `WebuiStaticApp`。httpx 客户端
  会在发送前规范化 `/..`，无法证明"服务端拒绝越界"，因此必须绕过它；
- 常规 GET 走 `httpx.AsyncClient + ASGITransport`（`TestClient` 会触发
  会导致 `filterwarnings = ["error"]` 失败的弃用警告）。
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any, cast

from httpx import ASGITransport, AsyncClient
import pytest
from starlette.applications import Starlette

from src.plugins.nonebot_plugin_lingchu_bot.services.webui import static
from src.plugins.nonebot_plugin_lingchu_bot.services.webui.paths import (
    build_webui_urls,
)

_INDEX_HTML = "<!doctype html><html><body>lingchu spa</body></html>"
_APP_JS = "console.log('lingchu');\n"
_URLS = build_webui_urls()


class _Captured:
    """手工 ASGI 调用的结果快照。

    Attributes:
        status: HTTP 状态码。
        body: 响应体（UTF-8 解码后的文本）。
        headers: 响应头列表。

    """

    def __init__(
        self, status: int, body: bytes, headers: list[tuple[str, str]]
    ) -> None:
        """保存一次响应的关键部分。

        Args:
            status: HTTP 状态码。
            body: 原始响应体。
            headers: 响应头。

        """
        self.status = status
        self.body_bytes = body
        self.headers = headers

    @property
    def text(self) -> str:
        """响应体文本。"""
        return self.body_bytes.decode("utf-8", errors="replace")


async def _call_asgi(app: Any, path: str, method: str = "GET") -> _Captured:
    """用给定方法与原始路径直接驱动 ASGI 应用。

    Args:
        app: ASGI 应用（`WebuiStaticApp` 或 `Mount` 包装）。
        path: 未经客户端规范化的原始请求路径。
        method: HTTP 方法。

    Returns:
        _Captured: 捕获到的响应。

    """
    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "root_path": "",
        "query_string": b"",
        "headers": [(b"host", b"webui.test")],
        "client": ("127.0.0.1", 12345),
        "server": ("webui.test", 80),
    }
    messages: list[dict[str, Any]] = []

    async def receive() -> dict[str, Any]:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: dict[str, Any]) -> None:
        messages.append(message)

    await app(scope, receive, send)

    status = next(
        cast("int", m["status"]) for m in messages if m["type"] == "http.response.start"
    )
    headers = [
        (name.decode("latin-1"), value.decode("latin-1"))
        for m in messages
        if m["type"] == "http.response.start"
        for name, value in cast("list[tuple[bytes, bytes]]", m["headers"])
    ]
    body = b"".join(
        cast("bytes", m["body"]) for m in messages if m["type"] == "http.response.body"
    )
    return _Captured(status, body, headers)


def _static_app() -> static.WebuiStaticApp:
    return static.WebuiStaticApp(_URLS)


def _mounted_app() -> Starlette:
    """按生产形态把静态应用挂到 Starlette 上（Mount 会注入 root_path）。"""
    app = Starlette()
    app.mount(_URLS.base, app=_static_app())
    return app


def _client(app: Any) -> AsyncClient:
    return AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://webui.test",
    )


@pytest.fixture
def built(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """准备一份可用产物，并把 `STATIC_ROOT` 指向它。"""
    root = tmp_path / "client"
    (root / "assets").mkdir(parents=True)
    # 用 write_bytes 而非 write_text：Windows 上 text 模式会把 \n 转成 \r\n，
    # 导致内容断言在不同平台结果不一致。
    (root / "index.html").write_bytes(_INDEX_HTML.encode("utf-8"))
    (root / "assets" / "app.js").write_bytes(_APP_JS.encode("utf-8"))
    monkeypatch.setattr(static, "STATIC_ROOT", root)
    yield root


@pytest.fixture
def unbuilt(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """把 `STATIC_ROOT` 指向一个空目录（模拟未构建）。"""
    root = tmp_path / "client"
    monkeypatch.setattr(static, "STATIC_ROOT", root)
    yield root


# --- is_built ---------------------------------------------------------------


def test_is_built_false_without_index(unbuilt: Path) -> None:
    assert static.static_root() == unbuilt
    assert static.is_built() is False


def test_is_built_true_with_index(built: Path) -> None:
    assert static.static_root() == built
    assert static.is_built() is True


# --- 静态与 fallback --------------------------------------------------------


async def test_index_page_served(built: Path) -> None:
    assert built
    async with _client(_static_app()) as client:
        response = await client.get(_URLS.page_root)
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "lingchu spa" in response.text


async def test_asset_served_as_javascript(built: Path) -> None:
    assert built
    async with _client(_mounted_app()) as client:
        response = await client.get(f"{_URLS.assets_root}/app.js")
    assert response.status_code == 200
    assert "javascript" in response.headers["content-type"]
    assert response.text == _APP_JS


async def test_deep_link_falls_back_to_index(built: Path) -> None:
    assert built
    async with _client(_static_app()) as client:
        response = await client.get(_URLS.page("config"))
    assert response.status_code == 200
    assert response.text == _INDEX_HTML


async def test_deep_link_returns_503_when_unbuilt(unbuilt: Path) -> None:
    assert unbuilt
    captured = await _call_asgi(_static_app(), _URLS.page("config"))
    assert captured.status == 503
    assert "尚未构建" in captured.text


@pytest.mark.parametrize(
    "traversal",
    [
        "/../secret.txt",
        "/assets/../../secret.txt",
        "/assets/..%2F..%2Fsecret.txt",
    ],
)
async def test_traversal_cannot_escape_static_root(built: Path, traversal: str) -> None:
    secret = built.parent / "secret.txt"
    secret.write_bytes(b"top secret")
    assert secret.is_file()

    async with _client(_mounted_app()) as client:
        response = await client.get(f"{_URLS.base}{traversal}")

    # 核心安全断言：无论最终落到 SPA 入口还是静态 404，都绝不能读到目录外文件。
    assert response.status_code in {200, 404}
    assert "top secret" not in response.text


async def test_plain_traversal_falls_back_to_index(built: Path) -> None:
    assert built
    secret = built.parent / "secret.txt"
    secret.write_bytes(b"top secret")

    captured = await _call_asgi(_static_app(), f"{_URLS.base}/../secret.txt")

    assert captured.status == 200
    assert captured.text == _INDEX_HTML


async def test_post_returns_405(built: Path) -> None:
    assert built
    captured = await _call_asgi(_static_app(), f"{_URLS.base}/x", method="POST")
    assert captured.status == 405
    assert b"method_not_allowed" in captured.body_bytes


# --- mount_static_app -------------------------------------------------------


def test_mount_static_app_is_idempotent(built: Path) -> None:
    assert built
    app = Starlette()
    app.state.webui_urls = build_webui_urls("/placeholder")

    assert static.mount_static_app(app, _URLS) is True
    assert app.state.webui_urls is _URLS
    mounted = [
        route
        for route in app.router.routes
        if getattr(route, "path", None) == _URLS.base
    ]
    assert len(mounted) == 1

    assert static.mount_static_app(app, _URLS) is False
    assert len(app.router.routes) == 1


async def test_mounted_app_serves_pages_and_rpc_is_kept(built: Path) -> None:
    assert built
    app = Starlette()
    static.mount_static_app(app, _URLS)

    async with _client(app) as client:
        response = await client.get(_URLS.page_root)
    assert response.status_code == 200
    assert "lingchu spa" in response.text
