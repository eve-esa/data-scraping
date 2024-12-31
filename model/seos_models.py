from typing import List
from pydantic import BaseModel

from model.base_models import BaseConfigScraper


class SeosSource(BaseModel):
    url: str
    chapters: int


class SeosConfig(BaseConfigScraper):
    sources: List[SeosSource]
