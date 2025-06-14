from pathlib import Path

import nonebot
from nonebot import get_plugin_config,logger
from nonebot.plugin import PluginMetadata

from .config import Config

__plugin_meta__ = PluginMetadata(
    name="lingchu-plugin",
    description="腾讯QQ社群管理用机器人插件",
    usage="",
    config=Config,
    type="application",
    homepage="",
)

config = get_plugin_config(Config)

sub_plugins = nonebot.load_plugins(
    str(Path(__file__).parent.joinpath("plugins").resolve())
)

logger.success("灵初插件加载成功")