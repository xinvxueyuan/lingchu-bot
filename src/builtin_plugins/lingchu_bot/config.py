from pathlib import Path
from tomllib import load

from pydantic import BaseModel


def get_version() -> str:
    try:
        with Path("pyproject.toml").open("rb") as f:
            return "v" + load(f).get("project", {}).get("version", "unknown")
    except FileNotFoundError:
        return "获取失败"


class Config(BaseModel):
    version: str = get_version()
