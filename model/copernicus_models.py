from typing import List

from model.base_iterative_publisher_models import (
    BaseIterativePublisherConfig,
    BaseIterativeWithConstraintPublisherJournal,
)


class CopernicusConfig(BaseIterativePublisherConfig):
    journals: List[BaseIterativeWithConstraintPublisherJournal]
