"""lingchu-bot核心插件主模块。

此模块是lingchu-bot的入口点，负责：
- 定义和导出NoneBot插件元数据
- 加载配置
- 注册核心运行时和管理命令

"""

from nonebot.plugin import PluginMetadata

from .core.config import Config
from .platforms import get_supported_adapters, iter_platform_profiles

__plugin_meta__ = PluginMetadata(
    name="lingchu-bot",
    description="跨平台群组管理机器人",
    usage=(
        "发送【菜单】或【menu】查看功能菜单。\n"
        "常用命令：\n"
        "- 禁言 @用户 [时长] [原因] / mute @user [duration] [reason]\n"
        "- 撤回 [@用户] [数量] / recall [@user] [count]\n"
        "- 远程禁言 <群号或群名称> @用户 [时长] / "
        "remote-mute <group> @user [duration]\n"
        "- 闭嘴 / 说话 (silence / speak)\n"
        "- 开机 / 关机 (boot / shutdown)\n"
        "中文与英文触发词按 locale 互斥，不会同时启用。"
    ),
    type="application",
    homepage="https://github.com/xinvxueyuan/lingchu-bot",
    config=None,
    supported_adapters=get_supported_adapters(),
    extra={
        "author": "xinvxueyuan",
        "maintainer": "xinvxueyuan",
        "priority": 50,
        "startup": True,
        "shutdown": True,
        "platforms": tuple(
            {
                "id": profile.platform_id,
                "name": profile.display_name,
                "capabilities": tuple(profile.capabilities),
                "adapters": tuple(sorted(profile.nonebot_adapters)),
            }
            for profile in iter_platform_profiles()
        ),
    },
)

# isort: off
from .database import toml_store as toml_store
from .database import models as models
from .database import orm_crud as orm_crud
from .database import sqlite_pragmas as sqlite_pragmas
from .services import message_store as message_store
from .start.startup import startup as startup

# Register runtime hooks after business modules because handlers depend on
# services.message_store and start.startup.
from . import hooks as hooks

# zhenxun 等宿主环境同时注册 150+ 插件的 Alconna 命令，默认上限 200 会被突破。
# 在 lingchu 自身命令注册前抬高全局上限，避免 ExceedMaxCount。
from arclet.alconna.config import config as _alconna_config

_ALCONNA_COMMAND_MAX_COUNT = 500

if getattr(_alconna_config, "command_max_count", 200) < _ALCONNA_COMMAND_MAX_COUNT:
    _alconna_config.command_max_count = _ALCONNA_COMMAND_MAX_COUNT
# isort: on

config = Config.from_nonebot()
