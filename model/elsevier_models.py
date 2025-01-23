from typing import List, TypeAlias, Dict
from pydantic import BaseModel, field_validator

from helper.base_enum import Enum
from model.base_models import BaseConfig


class SourceType(Enum):
    JOURNAL = "journal"
    ISSUE = "issue"


class ElsevierSource(BaseModel):
    url: str
    name: str
    type: str

    @field_validator("type")
    def validate_type(cls, v):
        if not v:
            raise ValueError("Type cannot be empty")
        if v not in SourceType:
            raise ValueError(f"Invalid type: {v}")
        return v


class ElsevierConfig(BaseConfig):
    base_url: str
    sources: List[ElsevierSource]


ElsevierScraperOutput: TypeAlias = Dict[str, List[str]]


class ElsevierScrapeIssueOutput(BaseModel):
    was_scraped: bool
    next_issue_url: str | None