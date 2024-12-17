from typing import Type, List
from bs4 import BeautifulSoup

from scrapers.base import BaseScraper, BaseModelScraper


class IOPModel(BaseModelScraper):
    pass


# TODO: popup automation not working
class IOPScraper(BaseScraper):
    """
    This class acts only on issues urls, because those are the only once identified in the data_collection gsheet
    """

    def scrape(self, model: IOPModel, scraper: BeautifulSoup) -> List:
        # Find all PDF links using appropriate class or tag
        pdf_links = scraper.find_all("a", href=lambda href: href and "/article/" in href)
        self.logger.info(f"PDF links found: {len(pdf_links)}")

        self.driver.quit()

        return pdf_links

    @property
    def model_class(self) -> Type[BaseModelScraper]:
        return IOPModel