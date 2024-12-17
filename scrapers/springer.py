import time
from typing import Type, List
from bs4 import BeautifulSoup

from scrapers.base import BaseScraper, BaseModelScraper


class SpringerModel(BaseModelScraper):
    pass


class SpringerScraper(BaseScraper):
    @property
    def model_class(self) -> Type[BaseModelScraper]:
        return SpringerModel

    def scrape(self, model: SpringerModel, scraper: BeautifulSoup) -> List:
        pass

    def post_process(self, links: List) -> List:
        return links

    def upload_to_s3(self, links: List):
        for link in links:
            self._s3_client.upload("iop", link)
            # Sleep after each successful download to avoid overwhelming the server
            time.sleep(5)
