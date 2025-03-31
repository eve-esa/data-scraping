import json
from abc import ABC, abstractmethod
from typing import Dict, Any, List
from pydantic import BaseModel as PydanticBaseModel, Field, field_validator
from datetime import datetime
from sqlalchemy import String, Text, Boolean, Integer
from sqlalchemy.dialects.mysql import LONGTEXT


class DatabaseFieldDefinition(PydanticBaseModel):
    type: Any
    nullable: bool = True
    default: Any = None

    # check that the `type` is not None
    @field_validator("type")
    def valid_type(cls, v):
        if not hasattr(v, "__visit_name__"):
            raise ValueError(f"\"type\" must be a valid SQLAlchemy type. Got {v}")
        return v


class DatabaseRelationDefinition(PydanticBaseModel):
    column_name: str
    referenced_table: str
    referenced_column: str


class BaseModel(PydanticBaseModel, ABC):
    id: int | None = None
    last_access_at: str | None = Field(default=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    @classmethod
    @abstractmethod
    def def_types(cls) -> Dict[str, DatabaseFieldDefinition]:
        pass

    @classmethod
    @abstractmethod
    def def_relations(cls) -> List[DatabaseRelationDefinition]:
        pass

    @classmethod
    @abstractmethod
    def table_name(cls) -> str:
        pass


class UploadedResource(BaseModel):
    scraper: str
    bucket_key: str
    source: str
    sha256: str | None = None
    content: bytes | None = None
    content_retrieved: bool | None = False
    success: bool | None = False
    message: str | None = None

    @classmethod
    def def_types(cls) -> Dict[str, DatabaseFieldDefinition]:
        return {
            "scraper": DatabaseFieldDefinition(type=String(length=255), nullable=False),
            "bucket_key": DatabaseFieldDefinition(type=Text, nullable=False),
            "source": DatabaseFieldDefinition(type=Text, nullable=False),
            "sha256": DatabaseFieldDefinition(type=String(length=255), default=None),
            "success": DatabaseFieldDefinition(type=Boolean, nullable=False, default=False),
            "content_retrieved": DatabaseFieldDefinition(type=Boolean, nullable=False, default=False),
            "message": DatabaseFieldDefinition(type=Text, default=None),
            "last_access_at": DatabaseFieldDefinition(type=String(length=255), nullable=False),
        }

    @classmethod
    def def_relations(cls) -> List[DatabaseRelationDefinition]:
        return []

    @classmethod
    def table_name(cls) -> str:
        return "uploaded_resources"


class ScraperOutput(BaseModel):
    scraper: str
    output: str

    @property
    def output_json(self) -> Dict:
        return json.loads(self.output)

    @classmethod
    def def_types(cls) -> Dict[str, DatabaseFieldDefinition]:
        return {
            "scraper": DatabaseFieldDefinition(type=String(length=255), nullable=False),
            "output": DatabaseFieldDefinition(type=LONGTEXT, nullable=False),
            "last_access_at": DatabaseFieldDefinition(type=String(length=255), nullable=False),
        }

    @classmethod
    def def_relations(cls) -> List[DatabaseRelationDefinition]:
        return []

    @classmethod
    def table_name(cls) -> str:
        return "scraper_outputs"


class ScraperFailure(BaseModel):
    scraper: str
    source: str
    message: str | None = None

    @classmethod
    def def_types(cls) -> Dict[str, DatabaseFieldDefinition]:
        return {
            "scraper": DatabaseFieldDefinition(type=String(length=255), nullable=False),
            "source": DatabaseFieldDefinition(type=Text, nullable=False),
            "message": DatabaseFieldDefinition(type=Text, default=None),
            "last_access_at": DatabaseFieldDefinition(type=String(length=255), nullable=False),
        }

    @classmethod
    def def_relations(cls) -> List[DatabaseRelationDefinition]:
        return []

    @classmethod
    def table_name(cls) -> str:
        return "scraper_failures"


class ScraperAnalytics(BaseModel):
    scraper: str
    result: str
    created_at: str | None = Field(default=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    @property
    def result_json(self) -> Dict:
        return json.loads(self.result)

    @classmethod
    def def_types(cls) -> Dict[str, DatabaseFieldDefinition]:
        return {
            "scraper": DatabaseFieldDefinition(type=String(length=255), nullable=False),
            "result": DatabaseFieldDefinition(type=LONGTEXT, nullable=False),
            "created_at": DatabaseFieldDefinition(type=String(length=255), nullable=False),
            "last_access_at": DatabaseFieldDefinition(type=String(length=255), nullable=False),
        }

    @classmethod
    def def_relations(cls) -> List[DatabaseRelationDefinition]:
        return []

    @classmethod
    def table_name(cls) -> str:
        return "scraper_analytics"


class UploadedResourceMetadata(BaseModel):
    uploaded_resource: UploadedResource
    metadata: str | None = None

    @property
    def metadata_json(self) -> Dict:
        return json.loads(self.metadata)

    @classmethod
    def def_types(cls) -> Dict[str, DatabaseFieldDefinition]:
        return {
            "uploaded_resource_id": DatabaseFieldDefinition(type=Integer, nullable=False),
            "metadata": DatabaseFieldDefinition(type=LONGTEXT, nullable=True),
            "last_access_at": DatabaseFieldDefinition(type=String(length=255), nullable=False),
        }

    @classmethod
    def def_relations(cls) -> List[DatabaseRelationDefinition]:
        return [
            DatabaseRelationDefinition(
                column_name="uploaded_resource_id",
                referenced_table=UploadedResource.table_name(),
                referenced_column="id",
            )
        ]

    @classmethod
    def table_name(cls) -> str:
        return "uploaded_resources_metadata"
