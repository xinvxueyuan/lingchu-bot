from nicegui import ui
from nonebot.log import logger


def mount_nicegui() -> None:
    ui.label("Hello NiceGUI!")


ui.run()
logger.info("NiceGUI mounted")
