from typing import List

from model.base_iterative_publisher_models import (
    BaseIterativeWithConstraintPublisherConfig,
    BaseIterativeWithConstraintPublisherJournal,
)


class AMSJournal(BaseIterativeWithConstraintPublisherJournal):
    url: str | None = None
    name: str
    code: str
    consecutive_missing_volumes_threshold: int | None = 3
    consecutive_missing_issues_threshold: int | None = 1


class AMSConfig(BaseIterativeWithConstraintPublisherConfig):
    journals: List[AMSJournal]
