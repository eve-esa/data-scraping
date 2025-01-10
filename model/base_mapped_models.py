from typing import List, TypeAlias
from pydantic import BaseModel

from helper.base_enum import Enum
from model.base_direct_publisher_models import BaseDirectPublisherConfig
from model.base_iterative_publisher_models import (
    BaseIterativePublisherJournal,
    BaseIterativePublisherConfig,
    BaseIterativeWithConstraintPublisherJournal,
)
from model.base_models import BaseConfig, Config
from model.base_pagination_publisher_models import BasePaginationPublisherSource, BasePaginationPublisherConfig
from model.base_url_publisher_models import BaseUrlPublisherSource, BaseUrlPublisherConfig


class SourceType(Enum):
    ITERATIVE = "iterative"
    ITERATIVE_WITH_CONSTRAINT = "iterative_with_constraint"
    PAGINATION = "pagination"
    URL = "url"
    DIRECT = "direct"


class BaseMappedItemSource(BaseModel):
    href: str | None = None
    class_: str | None = None


class BaseMappedIterativeJournal(BaseIterativePublisherJournal, BaseMappedItemSource):
    pass


class BaseMappedIterativeConfig(BaseIterativePublisherConfig):
    bucket_key: str | None = None
    journals: List[BaseMappedIterativeJournal]


class BaseMappedIterativeWithConstraintJournal(
    BaseIterativeWithConstraintPublisherJournal, BaseMappedItemSource
):
    pass


class BaseMappedIterativeWithConstraintConfig(BaseConfig):
    bucket_key: str | None = None
    journals: List[BaseMappedIterativeWithConstraintJournal]


class BaseMappedPaginationSource(BasePaginationPublisherSource, BaseMappedItemSource):
    page_size: int | None = None


class BaseMappedPaginationConfig(BasePaginationPublisherConfig):
    bucket_key: str | None = None
    sources: List[BaseMappedPaginationSource]


class BaseMappedUrlSource(BaseUrlPublisherSource, BaseMappedItemSource):
    pass


class BaseMappedUrlConfig(BaseUrlPublisherConfig):
    bucket_key: str | None = None
    sources: List[BaseMappedUrlSource]


class BaseMappedDirectConfig(BaseDirectPublisherConfig):
    bucket_key: str | None = None


BaseMappedSourceConfig: TypeAlias = (
    BaseMappedIterativeConfig
    | BaseMappedIterativeWithConstraintConfig
    | BaseMappedPaginationConfig
    | BaseMappedUrlConfig
    | BaseMappedDirectConfig
)


class BaseMappedSource(BaseModel):
    name: str
    scraper: str | None = None
    config: BaseMappedSourceConfig


class BaseMappedConfig(Config):
    sources: List[BaseMappedSource]
