from typing import List

from model.base_pagination_publisher_models import BasePaginationPublisherSource, BasePaginationPublisherConfig


class NCBISource(BasePaginationPublisherSource):
    pagination_url: str


class NCBIConfig(BasePaginationPublisherConfig):
    sources: List[NCBISource]
