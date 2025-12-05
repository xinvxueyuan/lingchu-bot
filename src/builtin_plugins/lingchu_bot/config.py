from pydantic import BaseModel


class Config(BaseModel):
    webui_enabled: bool = True
    webui_host: str = "127.0.0.1"
    webui_port: int = 8069
    webui_token: str = ""
    sub_plugins: list[str] = []
    core_plugins: list[str] = []
