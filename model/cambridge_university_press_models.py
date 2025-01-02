from typing import List

from model.base_pagination_publisher_models import BasePaginationPublisherSource
from scraper.base_scraper import BaseConfig


class CambridgeUniversityPressConfig(BaseConfig):
    sources: List[BasePaginationPublisherSource]
