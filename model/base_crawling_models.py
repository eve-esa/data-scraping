from typing import List, TypeAlias, Dict
from pydantic import BaseModel

from model.base_models import BaseConfig


class BaseCrawlingSource(BaseModel):
    name: str
    url: str


class BaseCrawlingConfig(BaseConfig):
    file_extension: str | None = ".html"
    sources: List[BaseCrawlingSource]


BaseCrawlingScraperOutput: TypeAlias = Dict[str, str]
