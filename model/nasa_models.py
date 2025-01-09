from typing import List

from model.base_mapped_models import BaseMappedPaginationSource, BaseMappedPaginationConfig


class NASANTRSSource(BaseMappedPaginationSource):
    page_size: int


class NASANTRSConfig(BaseMappedPaginationConfig):
    sources: List[NASANTRSSource]
