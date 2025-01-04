from abc import ABC
from pydantic import BaseModel


class ReadMoreButton(BaseModel):
    selector: str
    text: str


class Config(ABC, BaseModel):
    bucket_key: str


class BaseConfig(Config, ABC):
    base_url: str | None = None
    cookie_selector: str | None = None
    file_extension: str | None = ".pdf"
    read_more_button: ReadMoreButton | None = None
