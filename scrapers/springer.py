from typing import Type
from pydantic import BaseModel

from scrapers.base import BaseScraper


class SpringerModel(BaseModel):
    issue_url: str  # url contains volume and issue number. Eg: https://www.mdpi.com/2072-4292/1/3


class SpringerScraper(BaseScraper):
    def scrape(self, model: SpringerModel) -> list:
        pass

    @property
    def name(self) -> str:
        return "springer"

    @property
    def model_class(self) -> Type[BaseModel]:
        return SpringerModel
