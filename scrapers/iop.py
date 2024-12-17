from typing import Type
from bs4 import BeautifulSoup
import time
from pydantic import BaseModel

from scrapers.base import BaseScraper


class IOPModel(BaseModel):
    issue_url: str  # url contains volume and issue number. Eg: https://www.mdpi.com/2072-4292/1/3


# TODO: popoup automation not working
class IOPScraper(BaseScraper):
    """This class acts only on issues urls, because those are the only once identified in the data_collection gsheet"""

    def __call__(self, model: IOPModel) -> list:
        return self.scrape(model)

    # get paper url list from issue
    def scrape(self, model: IOPModel) -> list:
        """
        Get a list of URLs.

        Args:
            model (IOPModel): model containing the issue URL to scrape from IOPScience website
                (e.g. https://iopscience.iop.org/issue/1755-1315/540/1)
        Returns:
            list: list of markup urls referencing actual papers
        """

        issue_url = model.issue_url

        self.driver.get(issue_url)
        time.sleep(2)  # Give the page time to load

        # Handle cookie popup only once, for the first request
        if not self.cookie_handled:
            self._handle_cookie_popup()
            self.cookie_handled = True

        # Scroll through the page to load all articles
        self._scroll_page()

        # Get the fully rendered HTML and pass it to BeautifulSoup
        html = self.driver.page_source
        soup = BeautifulSoup(html, "html.parser")

        # Find all PDF links using appropriate class or tag
        pdf_links = soup.find_all("a", href=lambda href: href and "/article/" in href)
        self.logger.info(f"PDF links found: {len(pdf_links)}")

        return pdf_links

    @property
    def name(self) -> str:
        return "iop"

    @property
    def model_class(self) -> Type[BaseModel]:
        return IOPModel