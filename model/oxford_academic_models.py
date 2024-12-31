from typing import List

from model.base_iterative_publisher_models import BaseIterativePublisherJournal, BaseIterativePublisherConfig


class OxfordAcademicJournal(BaseIterativePublisherJournal):
    code: str
    start_volume: int
    end_volume: int
    start_issue: int
    end_issue: int


class OxfordAcademicConfig(BaseIterativePublisherConfig):
    journals: List[OxfordAcademicJournal]
