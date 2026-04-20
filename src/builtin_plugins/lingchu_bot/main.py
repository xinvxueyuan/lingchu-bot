from pathlib import Path

import nonebot
from nonebot import get_plugin_config
from nonebot.plugin import PluginMetadata

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

config = get_plugin_config(Config)

from . import core

core.index_init()

sub_plugins = nonebot.load_plugins(
    str(Path(__file__).parent.joinpath("plugins").resolve())
)

from .core.api import apimount as apimount
from .middleware.onebot11.event import MessageSentEvent as MessageSentEvent
