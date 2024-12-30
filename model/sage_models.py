from typing import List

from model.base_models import BaseConfigScraper
from model.base_pagination_publisher_models import BasePaginationPublisherSource


class SageConfig(BaseConfigScraper):
    sources: List[BasePaginationPublisherSource]
