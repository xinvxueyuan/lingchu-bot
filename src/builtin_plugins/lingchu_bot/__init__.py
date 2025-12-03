from nonebot import get_plugin_config, logger
from nonebot.plugin import PluginMetadata

from .config import Config
from .core.index import index_init
from .core.web.mount import BaseMount

__plugin_meta__ = PluginMetadata(
    name="lingchu-bot",
    description="最新可用的现代化QQ社区管理机器人，遵循onebot11规范",
    usage="",
    config=Config,
)

config = get_plugin_config(Config)

BaseMount()
index_init()


logger.info("插件加载完成,等待实例连接")
