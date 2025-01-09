from typing import List

from model.base_pagination_publisher_models import BasePaginationPublisherSource, BasePaginationPublisherConfig


class NASANTRSSource(BasePaginationPublisherSource):
    page_size: int


class NASANTRSConfig(BasePaginationPublisherConfig):
    sources: List[NASANTRSSource]
