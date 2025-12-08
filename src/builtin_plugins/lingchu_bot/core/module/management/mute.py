"""管理模块"""

from nonebot import on_command, require
from nonebot.permission import SUPERUSER
from nonebot.rule import RegexRule, Rule, StartswithRule

require("lingchu-bot")

muterule = Rule(StartswithRule(msg=("禁言", "解禁")), RegexRule(r"(?:^|\s|[^\d.])\d+$"))
mutecmd = on_command(
    "禁言", rule=muterule, permission=SUPERUSER, priority=5, block=True
)
unmutecmd = on_command(
    "解禁", rule=muterule, permission=SUPERUSER, priority=5, block=True
)
