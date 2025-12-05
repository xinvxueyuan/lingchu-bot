from nicegui import ui
from nonebot.log import logger


class BaseMount:
    def __init__(self) -> None:
        self.mount()

    def mount(self) -> None:
        ui.run(
            title="灵初web后台",
            dark=None,
            language="zh-CN",
            host="127.0.0.1",
            port=8096,
            # reload=False,
        )

        @ui.page("/")
        def _() -> None:
            ui.add_head_html(
                """
                <meta http-equiv="Refresh" content="0; url=/webui">
                <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
                <meta http-equiv="Pragma" content="no-cache">
                <meta http-equiv="Expires" content="0">
                """
            )
            logger.info("HTTP重定向到/webui")

        @ui.page("/webui")
        def _() -> None:
            with ui.header():
                ui.label("灵初 Web 后台")
                with ui.row():
                    ui.button("管理")
                    ui.button("刷新")
                    ui.button("保存")
                    ui.button("关于")
                    with ui.column():
                        ui.link("切换登录", "#")
                        ui.link("退出登录", "#")
