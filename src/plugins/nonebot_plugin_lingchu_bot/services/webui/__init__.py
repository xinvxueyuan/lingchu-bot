"""WebUI 动态运行时（nonebot 侧）路由注册。

在 NoneBot 驱动器启动后，将端点挂载到底层 Starlette 应用。导入本模块即
通过 ``on_startup`` 注册挂载逻辑；插件入口 ``__init__.py`` 末尾 import 本模块即可触发。
包含只读端点 + 简易字符串密码校验 + 登录密码校验端点 + 配置读写端点，
不实现任何 JWT/令牌功能。
"""

from __future__ import annotations

from nonebot import get_app, get_driver, logger

from .config_endpoints import (
    WEBUI_CONFIG_ADVANCED_PATH,
    WEBUI_CONFIG_BASIC_PATH,
    webui_config_advanced_endpoint,
    webui_config_basic_endpoint,
)
from .info import (
    WEBUI_INFO_PATH,
    WEBUI_ONEBOT_FRIENDS_PATH,
    WEBUI_ONEBOT_GROUPS_PATH,
    WEBUI_ONEBOT_LOGIN_INFO_PATH,
    WEBUI_ONEBOT_STATUS_PATH,
    WEBUI_ONEBOT_VERSION_INFO_PATH,
    WEBUI_QQ_NICKNAME_PATH,
    WEBUI_STATUS_PATH,
    WEBUI_TOOLS_COOKIES_PATH,
    WEBUI_TOOLS_CSRF_TOKEN_PATH,
    WEBUI_VERIFY_PASSWORD_PATH,
    webui_info_endpoint,
    webui_onebot_friends_endpoint,
    webui_onebot_groups_endpoint,
    webui_onebot_login_info_endpoint,
    webui_onebot_status_endpoint,
    webui_onebot_version_info_endpoint,
    webui_qq_nickname_endpoint,
    webui_status_endpoint,
    webui_tools_cookies_endpoint,
    webui_tools_csrf_token_endpoint,
    webui_verify_password_endpoint,
)

__all__ = [
    "register_webui_routes",
    "webui_config_advanced_endpoint",
    "webui_config_basic_endpoint",
    "webui_info_endpoint",
    "webui_onebot_friends_endpoint",
    "webui_onebot_groups_endpoint",
    "webui_onebot_login_info_endpoint",
    "webui_onebot_status_endpoint",
    "webui_onebot_version_info_endpoint",
    "webui_qq_nickname_endpoint",
    "webui_status_endpoint",
    "webui_tools_cookies_endpoint",
    "webui_tools_csrf_token_endpoint",
    "webui_verify_password_endpoint",
]


def register_webui_routes() -> None:
    """将 WebUI 端点挂载到 NoneBot 底层 Starlette 应用。"""
    app = get_app()
    routes = (
        (WEBUI_STATUS_PATH, webui_status_endpoint, ["GET"]),
        (WEBUI_INFO_PATH, webui_info_endpoint, ["GET"]),
        (WEBUI_QQ_NICKNAME_PATH, webui_qq_nickname_endpoint, ["GET"]),
        (WEBUI_TOOLS_COOKIES_PATH, webui_tools_cookies_endpoint, ["GET"]),
        (WEBUI_TOOLS_CSRF_TOKEN_PATH, webui_tools_csrf_token_endpoint, ["GET"]),
        (WEBUI_ONEBOT_LOGIN_INFO_PATH, webui_onebot_login_info_endpoint, ["GET"]),
        (WEBUI_ONEBOT_STATUS_PATH, webui_onebot_status_endpoint, ["GET"]),
        (WEBUI_ONEBOT_VERSION_INFO_PATH, webui_onebot_version_info_endpoint, ["GET"]),
        (WEBUI_ONEBOT_GROUPS_PATH, webui_onebot_groups_endpoint, ["GET"]),
        (WEBUI_ONEBOT_FRIENDS_PATH, webui_onebot_friends_endpoint, ["GET"]),
        (WEBUI_VERIFY_PASSWORD_PATH, webui_verify_password_endpoint, ["POST"]),
        (WEBUI_CONFIG_BASIC_PATH, webui_config_basic_endpoint, ["GET", "PUT"]),
        (WEBUI_CONFIG_ADVANCED_PATH, webui_config_advanced_endpoint, ["GET", "PUT"]),
    )
    for path, endpoint, methods in routes:
        if any(getattr(route, "path", None) == path for route in app.router.routes):
            logger.debug("WebUI 路由已存在，跳过注册: {}", path)
            continue
        app.router.add_route(path, endpoint, methods=methods)
        logger.debug("WebUI 路由已注册: {}", path)


@get_driver().on_startup
async def _on_startup() -> None:
    """在驱动器启动后挂载 WebUI 路由。"""
    register_webui_routes()
