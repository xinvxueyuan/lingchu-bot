from nonebot import get_plugin_config, logger
from nonebot.plugin import PluginMetadata

from .config import Config
from .core.index import index_init
from .core.web.mount import BaseMount

__plugin_meta__ = PluginMetadata(
    name="lingchu-bot",
    description="最新可用的现代化QQ社区管理机器人，遵循onebot11规范",
    usage="",
    type="application",
    supported_adapters={"nonebot.adapters.onebot.v11"},
    homepage="https://github.com/lingchu-bot/nonebot-plugin-lingchu-bot",
    config=Config,
)

config = get_plugin_config(Config)

index_init()
BaseMount()


logger.info("插件加载完成,等待实例连接")
