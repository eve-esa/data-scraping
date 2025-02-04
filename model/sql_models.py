import json
from abc import ABC, abstractmethod
from typing import Dict
from pydantic import BaseModel as PydanticBaseModel, Field
from datetime import datetime

from helper.base_enum import Enum


class DatabaseFieldType(Enum):
    TEXT = "TEXT"
    INTEGER = "INTEGER"
    VARCHAR = "VARCHAR"
    FLOAT = "FLOAT"


class BaseModel(PydanticBaseModel, ABC):
    id: int | None = None
    last_access_at: str | None = Field(default=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    @classmethod
    @abstractmethod
    def def_types(cls):
        pass


class UploadedResource(BaseModel):
    scraper: str
    bucket_key: str
    source: str
    sha256: str | None = None
    content: bytes | None = None

    @classmethod
    def def_types(cls):
        return {
            "scraper": DatabaseFieldType.VARCHAR,
            "bucket_key": DatabaseFieldType.TEXT,
            "source": DatabaseFieldType.TEXT,
            "sha256": DatabaseFieldType.VARCHAR,
            "last_access_at": DatabaseFieldType.VARCHAR
        }


class ScraperOutput(BaseModel):
    scraper: str
    output: str

    @property
    def output_json(self) -> Dict:
        return json.loads(self.output)

    @classmethod
    def def_types(cls):
        return {
            "scraper": DatabaseFieldType.VARCHAR,
            "output": DatabaseFieldType.TEXT,
            "last_access_at": DatabaseFieldType.VARCHAR
        }


class ScraperFailure(BaseModel):
    scraper: str
    source: str
    error: str | None = None

    @classmethod
    def def_types(cls):
        return {
            "scraper": DatabaseFieldType.VARCHAR,
            "source": DatabaseFieldType.TEXT,
            "error": DatabaseFieldType.TEXT,
            "last_access_at": DatabaseFieldType.VARCHAR
        }
