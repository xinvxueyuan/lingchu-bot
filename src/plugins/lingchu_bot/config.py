from pydantic import BaseModel


class Config(BaseModel):
    web_static_enabled: bool = True
    web_static_host: str = "127.0.0.1"
    web_static_port: int = 8081
