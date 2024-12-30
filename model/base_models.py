from abc import ABC
from pydantic import BaseModel


class BaseConfigScraper(ABC, BaseModel):
    bucket_key: str
