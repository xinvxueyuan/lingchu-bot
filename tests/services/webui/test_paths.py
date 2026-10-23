"""`services/webui/paths.py` 的单元测试：归一化规则、保留路径与 URL 派生。

覆盖点：
- 默认值回退（None / 空串 / 纯空白）；
- 归一化（补前导斜杠、折叠重复斜杠、去尾斜杠）；
- 非法配置抛出 `WebuiBasePathError`（字符集、遍历段、段长、段数）；
- 保留路径（大小写折叠）；
- `build_webui_urls` 的全部派生字段与拼接辅助方法。
"""

from __future__ import annotations

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.services.webui.paths import (
    DEFAULT_WEBUI_BASE_PATH,
    WebuiBasePathError,
    WebuiUrls,
    build_webui_urls,
    normalize_base_path,
)


@pytest.mark.parametrize("raw", [None, "", "   ", "\t\n"])
def test_normalize_falls_back_to_default(raw: str | None) -> None:
    assert DEFAULT_WEBUI_BASE_PATH == "/lc/webui"
    assert normalize_base_path(raw) == DEFAULT_WEBUI_BASE_PATH


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("lc/webui", "/lc/webui"),
        ("//lc//webui//", "/lc/webui"),
        ("/lc/webui/", "/lc/webui"),
        ("   /lc/webui   ", "/lc/webui"),
        ("///custom", "/custom"),
    ],
)
def test_normalize_accepts_and_canonicalizes(raw: str, expected: str) -> None:
    assert normalize_base_path(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "/lc/web ui",  # 含空格
        "/lc/%20ui",  # 含百分号编码
        "/lc/webui?x=1",  # 含查询分隔符
        "/lc/webui#frag",  # 含片段分隔符
        "/lc/./webui",  # 当前目录段
        "/lc/../webui",  # 上级目录段（路径遍历）
        "/" + "a" * 65,  # 单段超过 64 字符
        "/a/b/c/d/e/f/g",  # 段数超过 6
    ],
)
def test_normalize_rejects_invalid(raw: str) -> None:
    with pytest.raises(WebuiBasePathError) as excinfo:
        normalize_base_path(raw)
    assert excinfo.value.raw == raw
    assert excinfo.value.reason


@pytest.mark.parametrize(
    "raw",
    ["/", "/api", "/API", "/Api", "/onebot", "/OneBot", "/docs", "/DOCS"],
)
def test_normalize_rejects_reserved_paths_case_insensitively(raw: str) -> None:
    with pytest.raises(WebuiBasePathError):
        normalize_base_path(raw)


def test_build_webui_urls_defaults() -> None:
    urls = build_webui_urls()
    assert isinstance(urls, WebuiUrls)
    assert urls.base == "/lc/webui"
    assert urls.page_root == "/lc/webui/"
    assert urls.assets_root == "/lc/webui/assets"
    assert urls.rpc_root == "/lc/webui/v1/rpc"
    assert urls.legacy_root == "/lc/webui/v1"
    assert urls.cookie_path == "/lc/webui"
    assert urls.catch_all == "/lc/webui/{rest:path}"


def test_build_webui_urls_custom_base() -> None:
    urls = build_webui_urls("/assets/lc/ui")
    assert urls.base == "/assets/lc/ui"
    assert urls.page_root == "/assets/lc/ui/"
    assert urls.assets_root == "/assets/lc/ui/assets"
    assert urls.rpc_root == "/assets/lc/ui/v1/rpc"
    assert urls.legacy_root == "/assets/lc/ui/v1"
    assert urls.cookie_path == "/assets/lc/ui"
    assert urls.catch_all == "/assets/lc/ui/{rest:path}"
    assert urls.page("config") == "/assets/lc/ui/config"
    assert urls.rpc("/auth/login") == "/assets/lc/ui/v1/rpc/auth/login"


def test_page_and_rpc_helpers_with_default_base() -> None:
    urls = build_webui_urls()
    assert urls.page() == "/lc/webui/"
    assert urls.page("config") == "/lc/webui/config"
    assert urls.rpc("/auth/login") == "/lc/webui/v1/rpc/auth/login"


def test_build_webui_urls_rejects_invalid_base() -> None:
    with pytest.raises(WebuiBasePathError):
        build_webui_urls("/lc/../webui")
