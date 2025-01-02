from typing import List

from model.base_models import BaseConfig
from model.base_pagination_publisher_models import BasePaginationPublisherSource


class WileySource(BasePaginationPublisherSource):
    name: str
    base_url: str


class WileyConfig(BaseConfig):
    sources: List[WileySource]
