from typing import List

from model.base_pagination_publisher_models import BasePaginationPublisherSource, BasePaginationPublisherConfig


class WileySource(BasePaginationPublisherSource):
    name: str
    base_url: str


class WileyConfig(BasePaginationPublisherConfig):
    sources: List[WileySource]
