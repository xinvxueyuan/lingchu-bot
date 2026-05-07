from pathlib import Path

import nonebot
from nonebot import get_plugin_config
from nonebot.plugin import PluginMetadata
from nonebot.plugin.model import Plugin

from .config import Config

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

config: Config = get_plugin_config(Config)


sub_plugins: set[Plugin] = nonebot.load_plugins(
    str(Path(__file__).parent.joinpath("plugins").resolve())
)
