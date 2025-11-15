from nonebot import get_plugin_config, logger
from nonebot.plugin import PluginMetadata

from .config import Config
from .core.index import check_state, index_init
from .core.web.mount import mount_static_files

__plugin_meta__ = PluginMetadata(
    name="lingchu-bot",
    description="最新可用的现代化QQ社区管理机器人，遵循onebot11规范",
    usage="",
    config=Config,
)

config = get_plugin_config(Config)

if check_state() is True:
    logger.info("状态检查通过,等待实例连接")
    mount_static_files()
    index_init()
else:
    logger.error("状态检查失败，请勿直接启动nonebot2，需先配置.env文件")
