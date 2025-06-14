from pathlib import Path

import nonebot,time
from nonebot import get_plugin_config,logger
from nonebot.plugin import PluginMetadata

from .config import Config

__plugin_meta__ = PluginMetadata(
    name="lingchu-bot",
    description="灵初",
    usage="腾讯QQ社群管理用机器人插件",
    config=Config,
    type="application",
    homepage="https://github.com/xinvxueyuan/lingchu-bot",
    supported_adapters={"nonebot.adapters.onebot.v11"},
    extra={
        "author": "新v学员",
        "version": "0.1.0",
    },
)

config = get_plugin_config(Config)

sub_plugins = nonebot.load_plugins(
    str(Path(__file__).parent.joinpath("plugins").resolve())
)

plugin_config = get_plugin_config(Config)
logger.success("灵初插件已加载,当前状态:{}".format(
        "开启" if plugin_config.bot_state else "关闭"
    ))