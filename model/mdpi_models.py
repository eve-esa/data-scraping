from typing import List

from model.base_iterative_publisher_models import BaseIterativePublisherConfig, BaseIterativePublisherJournal


class MDPIJournal(BaseIterativePublisherJournal):
    end_volume: int | None = 16


class MDPIConfig(BaseIterativePublisherConfig):
    journals: List[MDPIJournal]
