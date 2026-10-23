"""WebUI 路径归一化与 URL 派生（单一真相源）。

WebUI 的所有对外路径——静态入口、静态资源、oRPC 路由、旧兼容端点、会话 Cookie
的 `Path`——都必须从本模块派生。任何消费方不得自行拼接前缀，否则
`LINGCHU_WEBUI_BASE_PATH` 一旦改成自定义值就会出现"页面能开、API 404"的漂移。

默认前缀为 `/lc/webui`：短且带命名空间，降低与同一端口上其它应用冲突的概率；
用户可通过 `LINGCHU_WEBUI_BASE_PATH` 指定任意合法前缀。
"""

from __future__ import annotations

from dataclasses import dataclass
import re

# 默认挂载前缀：`/lc/webui`（lc = lingchu）。
DEFAULT_WEBUI_BASE_PATH: str = "/lc/webui"

# 每个路径段允许的字符集。刻意偏严：只允许 RFC 3986 unreserved 字符与连字符，
# 拒绝空白、引号、百分号编码、查询/片段分隔符，以及任何可被解释为遍历的形态。
_SEGMENT_RE = re.compile(r"^[A-Za-z0-9._~-]+$")

# 保留前缀：这些路径由 NoneBot 自身或本插件的其它功能占用，WebUI 不得抢占，
# 否则会遮蔽真实的 API / 文档端点。
RESERVED_BASE_PATHS: frozenset[str] = frozenset({
    "/",
    "/api",
    "/onebot",
    "/docs",
    "/openapi.json",
    "/redoc",
    "/favicon.ico",
})

# 单个路径段的最大长度（防御超长 URL 造成的日志/存储噪声）。
_MAX_SEGMENT_LENGTH: int = 64
# base path 的最大段数（防御病态配置）。
_MAX_SEGMENTS: int = 6


class WebuiBasePathError(ValueError):
    """`LINGCHU_WEBUI_BASE_PATH` 非法。

    Attributes:
        raw: 用户配置的原始值。
        reason: 人类可读的拒绝原因。

    """

    def __init__(self, raw: str, reason: str) -> None:
        """记录原始配置值与拒绝原因。

        Args:
            raw: 用户配置的原始字符串。
            reason: 拒绝原因（中文，用于启动日志）。

        """
        self.raw = raw
        self.reason = reason
        super().__init__(f"invalid webui base path {raw!r}: {reason}")


@dataclass(frozen=True, slots=True)
class WebuiUrls:
    """由 base path 派生的全部对外路径。

    Attributes:
        base: 归一化后的前缀，形如 `/lc/webui`（无尾斜杠）。
        page_root: 页面入口，形如 `/lc/webui/`（**带**尾斜杠，保证相对资源解析）。
        assets_root: 静态资源目录前缀，形如 `/lc/webui/assets`。
        rpc_root: oRPC 路由前缀，形如 `/lc/webui/v1/rpc`。
        legacy_root: 旧兼容端点前缀，形如 `/lc/webui/v1`。
        cookie_path: 会话 Cookie 的 `Path`，等于 `base`（收窄到 WebUI 子树）。
        catch_all: SPA fallback 的 Starlette 路径模板。

    """

    base: str
    page_root: str
    assets_root: str
    rpc_root: str
    legacy_root: str
    cookie_path: str
    catch_all: str

    def page(self, rest: str = "") -> str:
        """拼接页面子路径（不含前导斜杠的 `rest`）。

        Args:
            rest: 相对页面入口的剩余路径，缺省为空表示页面根。

        Returns:
            str: 完整页面路径。

        """
        return f"{self.page_root}{rest}"

    def rpc(self, procedure: str) -> str:
        """拼接某条 oRPC 过程的完整路径。

        Args:
            procedure: 过程路径，形如 `/auth/login`。

        Returns:
            str: 完整的 RPC 路由路径。

        """
        return f"{self.rpc_root}{procedure}"


def normalize_base_path(raw: str | None) -> str:
    """把用户配置归一化为 `/<segments>` 形式的前缀。

    规则：
        - `None` 或空白 → 返回 `DEFAULT_WEBUI_BASE_PATH`；
        - 自动补前导 `/`，折叠重复 `/`，去掉尾部 `/`；
        - 每个路径段只允许 `[A-Za-z0-9._~-]`，且不得为 `.` / `..`；
        - 不得命中 `RESERVED_BASE_PATHS`；
        - 段数与段长有上限。

    非法输入**抛错**而非静默修正：静默修正会让"我明明配了这个路径"与
    "实际生效的是另一个路径"同时为真，是最难排查的一类配置问题。

    Args:
        raw: 用户配置的原始值（可能含多余斜杠、空白或非法字符）。

    Returns:
        str: 归一化后的前缀，无尾斜杠，非空。

    Raises:
        WebuiBasePathError: 配置为空串以外的非法值时抛出。

    """
    if raw is None:
        return DEFAULT_WEBUI_BASE_PATH
    text = raw.strip()
    if not text:
        return DEFAULT_WEBUI_BASE_PATH

    # 折叠重复斜杠并补齐前导斜杠，随后按段校验。
    text = f"/{text.lstrip('/')}"
    text = re.sub(r"/{2,}", "/", text).rstrip("/")
    if not text:
        raise WebuiBasePathError(raw, "前缀不能解析为根路径")

    segments = text.split("/")[1:]
    if len(segments) > _MAX_SEGMENTS:
        raise WebuiBasePathError(raw, f"路径段数不得超过 {_MAX_SEGMENTS}")

    for segment in segments:
        if segment in {".", ".."}:
            raise WebuiBasePathError(raw, "路径段不得为 . 或 ..")
        if not _SEGMENT_RE.match(segment):
            raise WebuiBasePathError(raw, f"路径段 {segment!r} 含非法字符")
        if len(segment) > _MAX_SEGMENT_LENGTH:
            raise WebuiBasePathError(raw, f"路径段长度不得超过 {_MAX_SEGMENT_LENGTH}")

    normalized = f"/{'/'.join(segments)}"
    if normalized.casefold() in {path.casefold() for path in RESERVED_BASE_PATHS}:
        raise WebuiBasePathError(raw, "命中 NoneBot / 插件保留路径")
    return normalized


def _resolve_base_path(raw: str | None) -> str:
    """归一化配置值，非法时降级为默认前缀。

    WebUI 是可选的附带功能，配置写错不应阻断 bot 启动，因此这里降级而非抛出。
    调用方（launcher）负责把降级事实反馈给用户。

    Args:
        raw: 用户配置的原始值。

    Returns:
        str: 归一化后的前缀；非法时返回默认前缀。

    """
    try:
        return normalize_base_path(raw)
    except WebuiBasePathError:
        return DEFAULT_WEBUI_BASE_PATH


def build_webui_urls(base_path: str | None = None) -> WebuiUrls:
    """由（可能未归一化的）前缀构造全部对外路径。

    Args:
        base_path: 前缀配置；`None` 表示使用默认值。

    Returns:
        WebuiUrls: 派生出的全部路径。

    Raises:
        WebuiBasePathError: `base_path` 非法时抛出（需要降级请先经
            `_resolve_base_path`）。

    """
    base = normalize_base_path(base_path)
    return WebuiUrls(
        base=base,
        page_root=f"{base}/",
        assets_root=f"{base}/assets",
        rpc_root=f"{base}/v1/rpc",
        legacy_root=f"{base}/v1",
        cookie_path=base,
        catch_all=f"{base}/{{rest:path}}",
    )
