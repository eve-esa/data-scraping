from typing import List
from pydantic import BaseModel

from model.base_models import BaseConfig


class SeosSource(BaseModel):
    url: str
    search: str
    folder: str
    chapter_start: int | None = 1
    chapters: int


class SeosConfig(BaseConfig):
    sources: List[SeosSource]
