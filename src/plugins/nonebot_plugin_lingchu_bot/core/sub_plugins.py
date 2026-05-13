from pathlib import Path

import nonebot
from nonebot.plugin import Plugin

sub_plugins: set[Plugin] = nonebot.load_plugins(
    str(object=Path(__file__).parent.joinpath("plugins").resolve())
)
