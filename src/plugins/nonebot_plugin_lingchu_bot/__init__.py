"""lingchu-bot核心插件主模块。

此模块是lingchu-bot的入口点，负责：
- 定义和导出NoneBot插件元数据
- 加载配置
- 发现并加载plugins目录下的所有子插件

"""

from nonebot import get_plugin_config
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
    config=Config,
    supported_adapters=get_supported_adapters(),
    extra={
        "author": [
            {"name": "lingchu-bot", "email": "support@xinvstar.xyz"},
            {"name": "xinvxueyuan", "email": "xinvxueyuan@yeah.net"},
        ],
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
from .database import json5_store as json5_store
from .database import models as models
from .database import orm_crud as orm_crud
from .services import message_store as message_store
from .start.startup import startup as startup

# Register runtime hooks after business modules because handlers depend on
# services.message_store and start.startup.
from . import hooks as hooks
# isort: on

config: Config = get_plugin_config(config=Config)
