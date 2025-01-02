from typing import List

from model.base_models import BaseConfig
from model.base_pagination_publisher_models import BasePaginationPublisherSource


class IEEEConfig(BaseConfig):
    sources: List[BasePaginationPublisherSource]
