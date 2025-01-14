from typing import List
from pydantic import BaseModel

from model.base_models import BaseConfig


class EOASource(BaseModel):
    url: str


class EOAConfig(BaseConfig):
    base_url: str
    sources: List[EOASource]
