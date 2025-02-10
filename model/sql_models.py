import json
from abc import ABC, abstractmethod
from typing import Dict, Any
from pydantic import BaseModel as PydanticBaseModel, Field
from datetime import datetime

from helper.base_enum import Enum


class DatabaseFieldType(Enum):
    TEXT = "TEXT"
    MEDIUMTEXT = "MEDIUMTEXT"
    LONGTEXT = "LONGTEXT"
    INTEGER = "INTEGER"
    VARCHAR = "VARCHAR"
    FLOAT = "FLOAT"
    BOOLEAN = "BOOLEAN"


class DatabaseFieldDefinition(PydanticBaseModel):
    type: DatabaseFieldType
    nullable: bool = True
    default: Any = None


class BaseModel(PydanticBaseModel, ABC):
    id: int | None = None
    last_access_at: str | None = Field(default=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    @classmethod
    @abstractmethod
    def def_types(cls) -> Dict[str, DatabaseFieldDefinition]:
        pass


class UploadedResource(BaseModel):
    scraper: str
    bucket_key: str
    source: str
    sha256: str | None = None
    content: bytes | None = None
    success: bool | None = True

    @classmethod
    def def_types(cls) -> Dict[str, DatabaseFieldDefinition]:
        return {
            "scraper": DatabaseFieldDefinition(type=DatabaseFieldType.VARCHAR, nullable=False),
            "bucket_key": DatabaseFieldDefinition(type=DatabaseFieldType.TEXT, nullable=False),
            "source": DatabaseFieldDefinition(type=DatabaseFieldType.TEXT, nullable=False),
            "sha256": DatabaseFieldDefinition(type=DatabaseFieldType.VARCHAR),
            "success": DatabaseFieldDefinition(type=DatabaseFieldType.BOOLEAN, nullable=False, default=False),
            "last_access_at": DatabaseFieldDefinition(type=DatabaseFieldType.VARCHAR),
        }


class ScraperOutput(BaseModel):
    scraper: str
    output: str

    @property
    def output_json(self) -> Dict:
        return json.loads(self.output)

    @classmethod
    def def_types(cls) -> Dict[str, DatabaseFieldDefinition]:
        return {
            "scraper": DatabaseFieldDefinition(type=DatabaseFieldType.VARCHAR, nullable=False),
            "output": DatabaseFieldDefinition(type=DatabaseFieldType.LONGTEXT, nullable=False),
            "last_access_at": DatabaseFieldDefinition(type=DatabaseFieldType.VARCHAR),
        }


class ScraperFailure(BaseModel):
    scraper: str
    source: str
    message: str | None = None

    @classmethod
    def def_types(cls) -> Dict[str, DatabaseFieldDefinition]:
        return {
            "scraper": DatabaseFieldDefinition(type=DatabaseFieldType.VARCHAR, nullable=False),
            "source": DatabaseFieldDefinition(type=DatabaseFieldType.TEXT, nullable=False),
            "message": DatabaseFieldDefinition(type=DatabaseFieldType.TEXT),
            "last_access_at": DatabaseFieldDefinition(type=DatabaseFieldType.VARCHAR),
        }


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
            "scraper": DatabaseFieldDefinition(type=DatabaseFieldType.VARCHAR, nullable=False),
            "result": DatabaseFieldDefinition(type=DatabaseFieldType.LONGTEXT, nullable=False),
            "created_at": DatabaseFieldDefinition(type=DatabaseFieldType.VARCHAR),
            "last_access_at": DatabaseFieldDefinition(type=DatabaseFieldType.VARCHAR),
        }
