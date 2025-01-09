from typing import List

from model.base_pagination_publisher_models import BasePaginationPublisherSource, BasePaginationPublisherConfig


class NasaNTRSSource(BasePaginationPublisherSource):
    page_size: int


class NasaNTRSConfig(BasePaginationPublisherConfig):
    sources: List[NasaNTRSSource]
