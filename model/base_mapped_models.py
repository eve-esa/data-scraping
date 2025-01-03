from typing import List
from pydantic import BaseModel, field_validator, model_validator

from base_enum import Enum
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
    href: str
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
    pass


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


class BaseMappedSource(BaseModel):
    name: str
    type: str
    config: (
            BaseMappedIterativeConfig
            | BaseMappedIterativeWithConstraintConfig
            | BaseMappedPaginationConfig
            | BaseMappedUrlConfig
            | BaseMappedDirectConfig
    )
    _type_config_mapper = {
        str(SourceType.ITERATIVE): BaseMappedIterativeConfig,
        str(SourceType.ITERATIVE_WITH_CONSTRAINT): BaseMappedIterativeWithConstraintConfig,
        str(SourceType.PAGINATION): BaseMappedPaginationConfig,
        str(SourceType.URL): BaseMappedUrlConfig,
        str(SourceType.DIRECT): BaseMappedDirectConfig
    }

    @field_validator("type")
    def validate_type(cls, v):
        if not v:
            raise ValueError("Type cannot be empty")
        if v not in SourceType:
            raise ValueError(f"Invalid type: {v}")
        return v

    @model_validator(mode="after")
    def validate_type_config(self):
        if not isinstance(self.config, self._type_config_mapper[self.type]):
            raise ValueError(f"Invalid config for type {self.type}")

        return self


class BaseMappedConfig(Config):
    sources: List[BaseMappedSource]
