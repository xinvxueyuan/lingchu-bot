"""WebUI 启动器：把静态资源与 oRPC 路由幂等地挂到 NoneBot 的 Web 应用上。

「启动WebUI」handle 与可选的自动挂载（`LINGCHU_WEBUI_AUTOMOUNT`）都走这里，
保证只有一套注册顺序、只有一份幂等判断：

1. 先注册 `orpc.build_procedure_routes(urls)` 的全部过程路由；
2. 再注册 `info.build_legacy_routes(urls)` 的三个 deprecated 兼容端点；
3. 最后 `static.mount_static_app(app, urls)` 挂静态应用。

顺序颠倒会让 SPA 兜底（Mount 到 base）先把 `{base}/v1/rpc/*` 吞成 HTML。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from nonebot import get_app, get_driver, logger

from .info import build_legacy_routes
from .orpc import build_procedure_routes
from .paths import (
    DEFAULT_WEBUI_BASE_PATH,
    WebuiBasePathError,
    WebuiUrls,
    build_webui_urls,
    normalize_base_path,
)
from .static import is_built, mount_static_app

# 通配监听地址在"可点击 URL"语境下没有意义，统一替换为回环地址。
_WILDCARD_HOSTS: frozenset[str] = frozenset({"0.0.0.0", "::", "[::]", ""})

# NoneBot 未显式配置端口时的默认值（与 nonebot.config.Config.port 一致）。
_DEFAULT_PORT: int = 8080

# 进程级挂载标志：与路由存在性双检，避免并发首次触发时重复注册。
# 用单元素容器承载而非 `global`，避免 PLW0603 且保持状态可变。
_mounted: list[bool] = [False]


@dataclass(frozen=True, slots=True)
class WebuiStatus:
    """一次「启动WebUI」的结果快照。

    Attributes:
        url: 可直接打开的页面地址。
        base_path: 实际生效的挂载前缀。
        built: 静态产物是否就绪。
        already_mounted: 本次调用前是否已挂载过。
        degraded: 配置的前缀非法、已回退默认值。
        reason: `degraded` / 未构建时的补充说明。

    """

    url: str
    base_path: str
    built: bool
    already_mounted: bool
    degraded: bool = False
    reason: str = ""


def _resolve_urls() -> tuple[WebuiUrls, bool, str]:
    """解析挂载前缀，非法配置降级为默认值。

    WebUI 是可选附带功能，配置写错不应阻断 bot 启动，因此这里降级而非抛出；
    降级事实通过返回值透传给调用方，由「启动WebUI」的回复告知用户。

    Returns:
        tuple[WebuiUrls, bool, str]: `(路径集合, 是否降级, 降级原因)`。

    """
    raw = getattr(_plugin_config(), "lingchu_webui_base_path", DEFAULT_WEBUI_BASE_PATH)
    try:
        normalized = normalize_base_path(str(raw))
    except WebuiBasePathError as error:
        logger.warning(
            "WebUI 前缀配置非法，已回退 {}: {}",
            DEFAULT_WEBUI_BASE_PATH,
            error.reason,
        )
        return build_webui_urls(DEFAULT_WEBUI_BASE_PATH), True, error.reason
    return build_webui_urls(normalized), False, ""


def _plugin_config() -> Any:
    """延迟导入插件配置，避免与本模块的导入顺序耦合。

    Returns:
        Any: 插件 `Config` 实例。

    """
    from ...core.config import plugin_config

    return plugin_config


def _display_host() -> str:
    """返回适合展示的主机名。

    Returns:
        str: 通配地址替换为 `127.0.0.1`，其余原样返回。

    """
    host = str(getattr(get_driver().config, "host", "") or "")
    return "127.0.0.1" if host in _WILDCARD_HOSTS else host


def _display_port() -> int:
    """返回驱动实际监听的端口。

    Returns:
        int: 端口号；未配置时回退 8080。

    """
    port = getattr(get_driver().config, "port", _DEFAULT_PORT)
    return port if isinstance(port, int) and port > 0 else _DEFAULT_PORT


def _is_route_registered(app: Any, path: str) -> bool:
    """判断某个路径是否已在应用的 router 上注册。

    Args:
        app: Starlette 应用。
        path: 待检查的路径。

    Returns:
        bool: 已注册时为真。

    """
    router = getattr(app, "router", None)
    for route in getattr(router, "routes", ()) or ():
        if getattr(route, "path", None) == path:
            return True
    return False


async def ensure_webui_mounted() -> WebuiStatus:
    """幂等地挂载 WebUI（oRPC 路由 + 静态应用）。

    重复调用返回同一份运行时状态，仅 `already_mounted` 为真，不会重复注册路由。

    Returns:
        WebuiStatus: 本次挂载的结果快照。

    """
    urls, degraded, reason = _resolve_urls()
    app = get_app()
    already = _mounted[0] or _is_route_registered(app, urls.base)

    if not already:
        # 顺序铁律：过程路由 → 兼容端点 → 静态挂载。
        # 兼容端点必须由本函数一并注册：automount 只走这里，漏掉就会让
        # {legacy_root}/* 在自动挂载模式下永远不存在。
        for path, endpoint, methods in (
            *build_procedure_routes(urls),
            *build_legacy_routes(urls),
        ):
            if _is_route_registered(app, path):
                logger.debug("WebUI 路由已存在，跳过注册: {}", path)
                continue
            app.router.add_route(path, endpoint, methods=methods)
        mount_static_app(app, urls)
        _mounted[0] = True
        logger.info(
            "WebUI 已挂载: {}",
            f"http://{_display_host()}:{_display_port()}{urls.page_root}",
        )

    built = is_built()
    if not built:
        reason = reason or "静态资源未构建"
    return WebuiStatus(
        url=f"http://{_display_host()}:{_display_port()}{urls.page_root}",
        base_path=urls.base,
        built=built,
        already_mounted=already,
        degraded=degraded,
        reason=reason,
    )


def webui_status_summary(status: WebuiStatus) -> str:
    """把状态快照渲染成一行用户可读文案。

    Args:
        status: `ensure_webui_mounted` 的返回值。

    Returns:
        str: 以「WebUI 已启动：」或「WebUI 已在运行：」开头的单行文本。

    """
    prefix = "WebUI 已在运行：" if status.already_mounted else "WebUI 已启动："
    text = f"{prefix}{status.url}"
    if not status.built:
        text += "（静态资源未构建，页面暂不可用，请安装包含 WebUI 的发行包）"
    if status.degraded:
        text += f"（配置的路径非法，已回退 {DEFAULT_WEBUI_BASE_PATH}）"
    return text


__all__ = [
    "WebuiStatus",
    "ensure_webui_mounted",
    "webui_status_summary",
]
