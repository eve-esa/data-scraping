from typing import List
from pydantic import BaseModel, field_validator

from base_enum import Enum
from scraper.base_scraper import BaseConfig


class SourceType(Enum):
    JOURNAL = "journal"
    ISSUE_OR_COLLECTION = "issue_or_collection"
    ARTICLE = "article"


class BaseUrlPublisherSource(BaseModel):
    url: str
    type: str

    @field_validator("type")
    def validate_type(cls, v):
        if not v:
            raise ValueError("Type cannot be empty")
        if v not in SourceType:
            raise ValueError(f"Invalid type: {v}")
        return v


class BaseUrlPublisherConfig(BaseConfig):
    sources: List[BaseUrlPublisherSource]
