from pydantic import BaseModel


class Config(BaseModel):
    version: str = "0.0.0-dev0"
