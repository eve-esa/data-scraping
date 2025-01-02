from typing import List

from model.base_models import BaseConfig
from model.base_pagination_publisher_models import BasePaginationPublisherSource


class NCBISource(BasePaginationPublisherSource):
    pagination_url: str


class NCBIConfig(BaseConfig):
    sources: List[NCBISource]
