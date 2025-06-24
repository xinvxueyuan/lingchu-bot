from pathlib import Path

import nonebot
from nonebot import get_plugin_config, logger, get_driver
from nonebot.plugin import PluginMetadata
from .config import Config

# 加载调度器插件
from nonebot import require
require("nonebot_plugin_apscheduler")



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

driver = get_driver()
plugin_config = get_plugin_config(Config)

sub_plugins = nonebot.load_plugins(
    str(Path(__file__).parent.joinpath("plugins").resolve())
)

from .core.init import *

# 将日志输出移到所有初始化完成后
logger.success(
    f"灵初插件已加载, 当前状态: {'开启' if plugin_config.plugins_state else '关闭'}"
)