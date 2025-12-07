from pydantic import BaseModel


class Config(BaseModel):
    online_bot_id: int | None = None
    online_bot_name: str = ""
    sub_plugins: list[str] = []
    core_plugins: list[str] = []
