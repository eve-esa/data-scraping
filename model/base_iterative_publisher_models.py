from typing import Dict, List, TypeAlias
from pydantic import BaseModel

from model.base_models import BaseConfig


class BaseIterativePublisherJournal(BaseModel):
    url: str
    name: str
    start_volume: int | None = 1
    end_volume: int | None = 30
    start_issue: int | None = 1
    end_issue: int | None = 30


class BaseIterativePublisherConfig(BaseConfig):
    journals: List[BaseIterativePublisherJournal]


class BaseIterativeWithConstraintPublisherJournal(BaseIterativePublisherJournal):
    consecutive_missing_volumes_threshold: int | None = 3
    consecutive_missing_issues_threshold: int | None = 3


class BaseIterativeWithConstraintPublisherConfig(BaseConfig):
    journals: List[BaseIterativeWithConstraintPublisherJournal]


IterativePublisherScrapeOutput: TypeAlias = Dict[str, Dict[int, Dict[int, List[str]]]]
IterativePublisherScrapeJournalOutput: TypeAlias = Dict[int, Dict[int, List[str]]]
IterativePublisherScrapeVolumeOutput: TypeAlias = Dict[int, List[str]]
IterativePublisherScrapeIssueOutput: TypeAlias = List[str]
