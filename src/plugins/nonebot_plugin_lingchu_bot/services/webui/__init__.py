"""WebUI 运行时装配（NoneBot 侧）。

改造后 WebUI 是"静态 SPA + oRPC 过程"，由 NoneBot 同进程托管，不再有独立 Node 服务端：

- `orpc.py`：全部数据过程（路径前缀由 `paths.py` 派生）；
- `static.py`：前端产物托管与 SPA 兜底；
- `info.py`：三个 deprecated 兼容端点；
- `launcher.py`：幂等挂载入口，供「启动WebUI」handle 与自动挂载复用。

**注册顺序铁律**：过程路由 → 兼容端点 → 最后静态挂载。静态挂载是 `Mount`，
会接管其下全部子路径，先注册就会把 RPC 请求吞成 HTML。
"""

from __future__ import annotations

from nonebot import get_app, get_driver, logger

from .info import build_legacy_routes
from .launcher import WebuiStatus, ensure_webui_mounted, webui_status_summary
from .orpc import build_procedure_routes
from .paths import (
    DEFAULT_WEBUI_BASE_PATH,
    WebuiBasePathError,
    WebuiUrls,
    build_webui_urls,
    normalize_base_path,
)
from .static import is_built, mount_static_app

__all__ = [
    "WebuiStatus",
    "build_webui_urls",
    "ensure_webui_mounted",
    "is_built",
    "register_webui_routes",
    "webui_status_summary",
]


def _resolve_urls() -> WebuiUrls:
    """解析挂载前缀，非法配置降级为默认值。

    Returns:
        WebuiUrls: 派生出的路径集合。

    """
    from ...core.config import plugin_config

    raw = getattr(plugin_config, "lingchu_webui_base_path", DEFAULT_WEBUI_BASE_PATH)
    try:
        return build_webui_urls(normalize_base_path(str(raw)))
    except WebuiBasePathError as error:
        logger.warning(
            "WebUI 前缀配置非法，已回退 {}: {}",
            DEFAULT_WEBUI_BASE_PATH,
            error.reason,
        )
        return build_webui_urls(DEFAULT_WEBUI_BASE_PATH)


def register_webui_routes() -> None:
    """把 WebUI 的全部路由与静态应用注册到 NoneBot 的 Starlette 应用上。

    幂等：已注册过的路径会被跳过，静态挂载同样由 `mount_static_app` 去重。
    """
    app = get_app()
    urls = _resolve_urls()

    for path, endpoint, methods in (
        *build_procedure_routes(urls),
        *build_legacy_routes(urls),
    ):
        if any(getattr(route, "path", None) == path for route in app.router.routes):
            logger.debug("WebUI 路由已存在，跳过注册: {}", path)
            continue
        app.router.add_route(path, endpoint, methods=methods)
        logger.debug("WebUI 路由已注册: {}", path)

    mount_static_app(app, urls)


@get_driver().on_startup
async def _on_startup() -> None:
    """按配置决定是否在启动时自动挂载 WebUI。

    默认只做提示、不挂载：给不需要 WebUI 的部署保持零额外路由。
    """
    from ...core.config import plugin_config

    if bool(getattr(plugin_config, "lingchu_webui_automount", False)):
        await ensure_webui_mounted()
        return
    logger.debug(
        "WebUI 未自动挂载；在群内发送「启动WebUI」即可启动，或设置 "
        "LINGCHU_WEBUI_AUTOMOUNT=true 随 bot 启动挂载。",
    )
