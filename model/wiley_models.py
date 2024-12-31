from typing import List

from model.base_models import BaseConfigScraper
from model.base_pagination_publisher_models import BasePaginationPublisherSource


class WileySource(BasePaginationPublisherSource):
    base_url: str


class WileyConfig(BaseConfigScraper):
    sources: List[WileySource]
