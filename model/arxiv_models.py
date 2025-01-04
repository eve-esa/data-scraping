from typing import List

from model.base_pagination_publisher_models import BasePaginationPublisherSource, BasePaginationPublisherConfig


class ArxivSource(BasePaginationPublisherSource):
    page_size: int


class ArxivConfig(BasePaginationPublisherConfig):
    sources: List[ArxivSource]
