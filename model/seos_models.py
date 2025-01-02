from typing import List
from pydantic import BaseModel

from model.base_models import BaseConfig


class SeosSource(BaseModel):
    url: str
    chapters: int


class SeosConfig(BaseConfig):
    sources: List[SeosSource]
