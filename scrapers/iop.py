from typing import Type, List
from pydantic import BaseModel

from scrapers.base import BaseScraper


class IOPModel(BaseModel):
    issue_url: str  # url contains volume and issue number. Eg: https://www.mdpi.com/2072-4292/1/3


# TODO: popup automation not working
class IOPScraper(BaseScraper):
    """This class acts only on issues urls, because those are the only once identified in the data_collection gsheet"""

    def __call__(self, model: IOPModel) -> List:
        scraper = self._setup_scraper(model.issue_url)

        # Find all PDF links using appropriate class or tag
        pdf_links = scraper.find_all("a", href=lambda href: href and "/article/" in href)
        self.logger.info(f"PDF links found: {len(pdf_links)}")

        self.driver.quit()

        return pdf_links

    @property
    def model_class(self) -> Type[BaseModel]:
        return IOPModel