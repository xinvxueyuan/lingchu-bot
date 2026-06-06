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
    usage="",
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
        "version": "0.0.0",
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

from .database import json5_store as json5_store
from .database import models as models
from .database import orm_crud as orm_crud
from .services import messagestore as messagestore
from .start.startup import startup as startup

config: Config = get_plugin_config(config=Config)
