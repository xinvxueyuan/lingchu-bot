"""lingchu-bot核心插件主模块。

此模块是lingchu-bot的入口点，负责：
- 定义和导出NoneBot插件元数据
- 加载配置
- 发现并加载plugins目录下的所有子插件

"""

from nonebot import get_plugin_config
from nonebot.plugin import PluginMetadata

from .core.config import Config

__plugin_meta__ = PluginMetadata(
    name="lingchu-bot",
    description="lingchu-bot",
    usage="",
    type="application",
    homepage="https://github.com/lingchu-bot/lingchu-bot",
    config=Config,
    supported_adapters={"~onebot.v11", "~milky"},
    extra={
        "author": [
            {"name": "lingchu-bot", "email": "support@xinvstar.xyz"},
            {"name": "xinvxueyuan", "email": "xinvxueyuan@yeah.net"},
        ],
        "maintainer": "xinvxueyuan",
        "version": "0.0.0-dev0",
        "priority": 50,
        "startup": True,
        "shutdown": True,
    },
)

from .database import json5_store as json5_store
from .database import orm_crud as orm_crud

config: Config = get_plugin_config(config=Config)
