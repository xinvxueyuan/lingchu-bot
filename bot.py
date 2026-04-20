import nonebot
from nonebot.adapters.github import Adapter as GITHUBAdapter
from nonebot.adapters.milky import Adapter as MILKYAdapter
from nonebot.adapters.onebot.v11 import Adapter as ONEBOT_V11Adapter

init_config = {"LOCALSTORE_USE_CWD": True, "DRIVER": "~fastapi+~httpx+~websockets"}
nonebot.init(init_config=init_config)
app = nonebot.get_asgi()

driver = nonebot.get_driver()
driver.register_adapter(ONEBOT_V11Adapter)
driver.register_adapter(GITHUBAdapter)
driver.register_adapter(MILKYAdapter)

nonebot.load_from_toml("pyproject.toml")
nonebot.load_plugins("src/builtin_plugins")

if __name__ == "__main__":
    nonebot.run()
