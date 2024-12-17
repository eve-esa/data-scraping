from typing import Type, List
from bs4 import BeautifulSoup

from scrapers.base import BaseScraper, BaseModelScraper


class SpringerModel(BaseModelScraper):
    pass


class SpringerScraper(BaseScraper):
    def scrape(self, model: SpringerModel, scraper: BeautifulSoup) -> List:
        pass

    @property
    def model_class(self) -> Type[BaseModelScraper]:
        return SpringerModel
