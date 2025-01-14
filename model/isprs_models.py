from typing import List
from pydantic import BaseModel

from model.base_models import BaseConfig


class ISPRSSource(BaseModel):
    url: str


class ISPRSConfig(BaseConfig):
    sources: List[ISPRSSource]
