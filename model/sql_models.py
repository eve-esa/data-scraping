import json
from typing import Dict
from pydantic import BaseModel as PydanticBaseModel, Field
from datetime import datetime


class BaseModel(PydanticBaseModel):
    id: int | None = None
    last_access_at: str | None = Field(default=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))


class Resource(BaseModel):
    scraper: str
    bucket_key: str
    source: str
    sha256: str | None = None
    content: bytes | None = None


class Output(BaseModel):
    scraper: str
    output: str

    @property
    def output_json(self) -> Dict:
        return json.loads(self.output)