import nonebot
from nicegui import ui
from nonebot import require

require("lingchu_bot")


ui.run_with(
    app=nonebot.get_asgi(),
    mount_path="/webui",
    title="灵初web后台",
    dark=None,
    language="zh-CN",
)


class BaseMount:
    def __init__(self) -> None:
        self.mount()

    def mount(self) -> None:
        @ui.page("/")
        def _() -> None:
            with ui.header():
                ui.label("灵初 Web 后台")
            with ui.row():
                ui.button("刷新")
                ui.button("保存")
                ui.button("关于")
