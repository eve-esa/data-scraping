from typing import TypeAlias, Dict, List
from pydantic import BaseModel

from model.base_models import BaseConfig


class BasePaginationPublisherSource(BaseModel):
    """
    Configuration model for the base pagination publisher scraper source. The `landing_page_url` is the URL to scrape to
    get the initial pagination URL.

    Variables:
        landing_page_url (str): The landing URL to scrape
    """
    landing_page_url: str
    page_size: int | None = None


class BasePaginationPublisherConfig(BaseConfig):
    sources: List[BasePaginationPublisherSource]


BasePaginationPublisherScrapeOutput: TypeAlias = Dict[str, List[str]]
