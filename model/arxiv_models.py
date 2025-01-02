from typing import List

from model.base_models import BaseConfig
from model.base_pagination_publisher_models import BasePaginationPublisherSource


class ArxivSource(BasePaginationPublisherSource):
    page_size: int


class ArxivConfig(BaseConfig):
    sources: List[ArxivSource]
