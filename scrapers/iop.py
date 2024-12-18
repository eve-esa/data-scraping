import time
from typing import Type, List
from bs4 import ResultSet

from scrapers.base import BaseScraper, BaseConfigScraper


class IOPJournal(BaseConfigScraper):
    issue_url: str  # url contains volume and issue number. Eg: https://www.mdpi.com/2072-4292/1/3


class IOPConfig(BaseConfigScraper):
    issues: List[IOPJournal]


# TODO: popup automation not working
class IOPScraper(BaseScraper):
    """
    This class acts only on issues urls, because those are the only once identified in the data_collection gsheet
    """

    @property
    def model_class(self) -> Type[BaseConfigScraper]:
        return IOPConfig

    def scrape(self, model: IOPConfig) -> List[ResultSet]:
        pdf_links = []
        for journal in model.issues:
            pdf_links.extend(self.__scrape_issue(journal))

        return pdf_links

    def post_process(self, links: ResultSet) -> List[str]:
        return [link.get("href") for link in links]

    def upload_to_s3(self, links: ResultSet):
        for link in links:
            self._s3_client.upload("iop", link.get("href"))
            # Sleep after each successful download to avoid overwhelming the server
            time.sleep(5)

    def __scrape_issue(self, journal: IOPJournal) -> List[ResultSet]:
        scraper = self._setup_scraper(journal.issue_url)

        # Find all PDF links using appropriate class or tag
        pdf_links = scraper.find_all("a", href=lambda href: href and "/article/" in href)
        self._logger.info(f"PDF links found: {len(pdf_links)}")

        self._driver.quit()

        return pdf_links
