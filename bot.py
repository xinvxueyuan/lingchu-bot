import nonebot
from nicegui import ui
from nonebot.adapters.onebot.v11 import Adapter as ONEBOT_V11Adapter

nonebot.init()

app = nonebot.get_asgi()

driver = nonebot.get_driver()
driver.register_adapter(ONEBOT_V11Adapter)

ui.run_with(app, mount_path="/rewebui")

nonebot.load_from_toml("pyproject.toml")

if __name__ == "__main__":
    nonebot.run(app="__main__:app")
