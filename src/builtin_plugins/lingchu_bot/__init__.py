from pathlib import Path

import nonebot
from nonebot import get_plugin_config
from nonebot.plugin import PluginMetadata

from .config import Config
from .core.index import index_init

__plugin_meta__ = PluginMetadata(
    name="lingchu-bot",
    description="最新可用的现代化管理机器人",
    usage="",
    type="application",
    supported_adapters={"nonebot.adapters.onebot.v11"},
    homepage="https://github.com/lingchu-bot/nonebot-plugin-lingchu-bot",
    config=Config,
)

config = get_plugin_config(Config)

index_init()


sub_plugins = nonebot.load_plugins(
    str(Path(__file__).parent.joinpath("plugins").resolve())
)
