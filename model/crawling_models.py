from typing import List, TypeAlias, Dict
from pydantic import BaseModel

from model.base_models import BaseConfig


class CrawlingSource(BaseModel):
    name: str
    url: str


class CrawlingConfig(BaseConfig):
    file_extension: str | None = ".html"
    sources: List[CrawlingSource]


CrawlingScraperOutput: TypeAlias = Dict[str, str]
