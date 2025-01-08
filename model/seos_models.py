from typing import List
from pydantic import BaseModel

from model.base_models import BaseConfig


class SeosSource(BaseModel):
    url: str
    search: str
    folder: str
    chapters: int


class SeosConfig(BaseConfig):
    sources: List[SeosSource]
