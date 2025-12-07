import nonebot
from nicegui import ui
from nonebot import require

require("lingchu_bot")
from nonebot import get_plugin_config

from ...config import Config

webui_config = get_plugin_config(Config)
global_config = nonebot.get_driver().config

if True:
    web_env = global_config.environment == "prod"
    ui.run_with(
        app=nonebot.get_asgi(),
        mount_path="/webui",
        title="灵初web后台",
        dark=None,
        # storage_secret=webui_config.webui_token,
        prod_js=web_env,
        language="zh-CN",
    )


class BaseMount:
    def __init__(self) -> None:
        self.index()

    def index(self) -> None:
        @ui.page("/")
        def _() -> None:
            with ui.header():
                ui.label("灵初 Web 后台")
            with ui.row():
                ui.button("刷新")
                ui.button("保存")
                ui.button("关于")
