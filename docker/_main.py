import importlib

import nonebot

importlib.import_module("bot")

app = nonebot.get_asgi()
