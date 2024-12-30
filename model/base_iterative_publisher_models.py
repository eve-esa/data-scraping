from typing import Dict, List, TypeAlias
from pydantic import BaseModel

from model.base_models import BaseConfigScraper


IterativePublisherScrapeOutput: TypeAlias = Dict[str, Dict[int, Dict[int, List[str]]]]
IterativePublisherScrapeJournalOutput: TypeAlias = Dict[int, Dict[int, List[str]]]
IterativePublisherScrapeVolumeOutput: TypeAlias = Dict[int, List[str]]
IterativePublisherScrapeIssueOutput: TypeAlias = List[str]


class BaseIterativePublisherJournal(BaseModel):
    url: str
    name: str
    start_volume: int | None = 1
    end_volume: int | None = 30
    start_issue: int | None = 1
    end_issue: int | None = 30


class BaseIterativeWithConstraintPublisherJournal(BaseIterativePublisherJournal):
    consecutive_missing_issues_threshold: int | None = 3


class BaseIterativePublisherConfig(BaseConfigScraper):
    journals: List[BaseIterativePublisherJournal]
