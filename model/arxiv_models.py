from typing import List

from model.base_models import BaseConfigScraper
from model.base_pagination_publisher_models import BasePaginationPublisherSource


class ArxivSource(BasePaginationPublisherSource):
    page_size: int


class ArxivConfig(BaseConfigScraper):
    sources: List[ArxivSource]
