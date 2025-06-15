from pathlib import Path

import nonebot
from nonebot import get_plugin_config,logger,get_driver
from nonebot.plugin import PluginMetadata
from nonebot.adapters.onebot.v11 import Bot
from .config import Config

from .core.init import *

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

driver = get_driver()
global_config = driver.config
plugin_config = Config(**global_config.dict())

plugin_config = get_plugin_config(Config)
logger.success("灵初插件已加载,当前状态:{}".format(
        "开启" if plugin_config.bot_state else "关闭"
    ))

async def get_bot_id(bot: Bot):
    """获取当前机器人ID并赋值给配置"""
    current_id = str(bot.self_id)
    if plugin_config.bot_id:
        if plugin_config.bot_id != current_id:
            logger.error(f"机器人ID不匹配! 配置中的ID: {plugin_config.bot_id}, 当前ID: {current_id}")
            plugin_config.bot_state = False
    plugin_config.bot_id = current_id
    return plugin_config.bot_id