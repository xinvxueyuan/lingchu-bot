"""WebUI 静态资源托管与 SPA fallback。

前端产物（`webui/dist/client`）随 Python 包一起发布，由 NoneBot 同进程托管：

- `{base}/assets/*` 走 `StaticFiles`（文件名带构建哈希，可长缓存）；
- 其余 `GET {base}/*` 回落到 `index.html`，交给前端路由处理（深链刷新不 404）；
- `{base}`（无尾斜杠）由挂载点自身的重定向处理，页面内相对资源因此总能解析。

**路由顺序**：静态挂载必须最后注册。`{base}` 这个 Mount 会接管其下所有子路径，
先注册就会把 oRPC 请求吞成 HTML。
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from nonebot import logger
from starlette.responses import FileResponse, JSONResponse, Response
from starlette.staticfiles import StaticFiles

if TYPE_CHECKING:
    from starlette.routing import Router
    from starlette.types import Receive, Scope, Send

    from .paths import WebuiUrls

# 前端产物落点：services/webui/static.py → 插件包根 → webui/dist/client。
# 该路径由 scripts/stage_webui.mjs 在构建期写入，随 wheel 一起分发。
STATIC_ROOT: Path = (
    Path(__file__).resolve().parent.parent.parent / "webui" / "dist" / "client"
)
INDEX_FILE: str = "index.html"
ASSETS_SEGMENT: str = "assets/"

# 产物缺失时的提示（面向运维，而不是面向浏览器用户）。
_NOT_BUILT_HINT: str = (
    "WebUI 静态资源尚未构建。请安装包含 WebUI 的发行包，"
    "或在源码环境执行 pnpm webui:build && pnpm webui:stage。"
)


def static_root() -> Path:
    """返回前端产物目录。

    Returns:
        Path: `<plugin>/webui/dist/client`。

    """
    return STATIC_ROOT


def is_built() -> bool:
    """判断前端产物是否就绪。

    Returns:
        bool: `index.html` 存在时为真。

    """
    return (STATIC_ROOT / INDEX_FILE).is_file()


def _safe_join(rest: str) -> Path | None:
    """把请求路径安全地拼到产物目录下。

    Args:
        rest: 去掉 base 前缀后的剩余路径。

    Returns:
        Path | None: 合法时返回绝对路径；疑似穿越或越界时返回 None。

    """
    if not rest:
        return None
    root = STATIC_ROOT.resolve()
    candidate = (root / rest).resolve()
    if candidate == root or root not in candidate.parents:
        return None
    return candidate


class WebuiStaticApp:
    """挂载在 base 前缀下的 ASGI 应用：静态资源 + SPA fallback。

    用它而不是给 Starlette 顶层注册 `{rest:path}`，可以把 WebUI 的兜底范围
    严格限制在自己的前缀内，不会劫持 NoneBot 的其它路由。

    Attributes:
        urls: 路径集合。

    """

    def __init__(self, urls: WebuiUrls) -> None:
        """构造配套的静态应用。

        Args:
            urls: 由 base path 派生的路径集合。

        """
        self.urls = urls
        self._prefix = f"{urls.base}/"
        self._assets = StaticFiles(
            directory=str(STATIC_ROOT / "assets"),
            check_dir=False,
        )

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """ASGI 入口。

        Args:
            scope: ASGI 作用域。
            receive: ASGI 消息接收器。
            send: ASGI 消息发送器。

        """
        if scope["type"] != "http":
            return
        method = cast("str", scope.get("method", "GET"))
        path = cast("str", scope.get("path", ""))

        if method not in {"GET", "HEAD"}:
            await _method_not_allowed()(scope, receive, send)
            return

        relative = path[len(self._prefix) :] if path.startswith(self._prefix) else ""
        if relative.startswith(ASSETS_SEGMENT):
            # StaticFiles 用 `get_route_path(scope)`（path 去掉 root_path）当相对路径，
            # 而目录已固定在 `.../assets`，故必须把 root_path 推进到 assets 段，
            # 否则会解析成 `assets/assets/xxx` 并 404。
            asset_scope = dict(scope)
            asset_scope["root_path"] = f"{self.urls.base}/{ASSETS_SEGMENT.rstrip('/')}"
            await self._assets(asset_scope, receive, send)
            return

        candidate = _safe_join(relative)
        if candidate is not None and candidate.is_file():
            await _file_response(candidate)(scope, receive, send)
            return

        await _index_response(scope, receive, send)


def _method_not_allowed() -> JSONResponse:
    """非 GET/HEAD 请求的响应。

    Returns:
        JSONResponse: 405 错误。

    """
    return JSONResponse(
        status_code=405,
        content={"error": {"code": "method_not_allowed"}},
    )


def _file_response(candidate: Path) -> FileResponse:
    """为产物中的真实文件构造响应。

    Args:
        candidate: 已校验位于产物目录内的文件路径。

    Returns:
        FileResponse: 文件响应。

    """
    return FileResponse(candidate)


async def _index_response(scope: Scope, receive: Receive, send: Send) -> None:
    """返回 SPA 入口页；产物缺失时给出明确的 503 文本。

    Args:
        scope: ASGI 作用域。
        receive: ASGI 消息接收器。
        send: ASGI 消息发送器。

    """
    if not is_built():
        response: Response = Response(
            _NOT_BUILT_HINT,
            status_code=503,
            media_type="text/plain; charset=utf-8",
        )
    else:
        response = FileResponse(
            STATIC_ROOT / INDEX_FILE,
            media_type="text/html; charset=utf-8",
            headers={"cache-control": "no-cache"},
        )
    await response(scope, receive, send)


def mount_static_app(app: Any, urls: WebuiUrls) -> bool:
    """把 WebUI 静态应用挂到 NoneBot 的 Starlette 应用上。

    必须在该应用上、所有 oRPC 路由注册**之后**调用。

    Args:
        app: NoneBot 底层 Starlette 应用。
        urls: 由 base path 派生的路径集合。

    Returns:
        bool: 首次挂载返回 True；已存在同前缀挂载返回 False（幂等）。

    """
    from starlette.routing import Mount

    router = cast("Router", app.router)
    if any(
        isinstance(route, Mount) and getattr(route, "path", None) == urls.base
        for route in router.routes
    ):
        logger.debug("WebUI 静态挂载已存在，跳过: {}", urls.base)
        return False
    app.state.webui_urls = urls
    router.mount(urls.base, app=WebuiStaticApp(urls))
    logger.debug("WebUI 静态应用已挂载: {}", urls.base)
    return True
