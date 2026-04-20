"""全局分页工具。"""

from pydantic import BaseModel, Field


class Pagination(BaseModel):
    """通用分页参数。"""

    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
