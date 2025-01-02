from abc import ABC
from pydantic import BaseModel


class BaseConfig(ABC, BaseModel):
    bucket_key: str
    base_url: str | None = None
    cookie_selector: str | None = None
    file_extension: str | None = ".pdf"
