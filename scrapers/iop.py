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
        """
        Return the configuration model class.

        Returns:
            Type[BaseConfigScraper]: The configuration model class.
        """
        return IOPConfig

    @property
    def cookie_selector(self) -> str:
        return "body > div.cky-consent-container.cky-classic-bottom > div.cky-consent-bar > div > div > div.cky-notice-btn-wrapper > button.cky-btn.cky-btn-accept"

    def scrape(self, model: IOPConfig) -> List[ResultSet]:
        """
        Scrape the IOP issue URLs of for PDF links.

        Args:
            model (IOPConfig): The configuration model.

        Returns:
            List[ResultSet]: A list of ResultSet objects containing the PDF links.
        """
        pdf_links = []
        for journal in model.issues:
            pdf_links.extend(self.__scrape_issue(journal))

        return pdf_links

    def post_process(self, links: ResultSet) -> List[str]:
        """
        Extract the href attribute from the links.

        Args:
            links (ResultSet): A ResultSet object containing the PDF links.

        Returns:
            List[str]: A list of strings containing the PDF links
        """
        return [link.get("href") for link in links]

    def upload_to_s3(self, links: ResultSet):
        """
        Upload the PDF files to S3.

        Args:
            links (ResultSet): A ResultSet object containing the PDF links.
        """
        self._logger.info("Uploading files to S3")

        for link in links:
            result = self._s3_client.upload("iop", link.get("href"))
            if not result:
                self._done = False

            # Sleep after each successful download to avoid overwhelming the server
            time.sleep(5)

    def __scrape_issue(self, journal: IOPJournal) -> List[ResultSet]:
        """
        Scrape the issue URL for PDF links.

        Args:
            journal (IOPJournal): The journal to scrape.

        Returns:
            List[ResultSet]: A list of ResultSet objects containing the PDF links.
        """
        self._logger.info(f"Processing Issue URL {journal.issue_url}")

        scraper = self._setup_scraper(journal.issue_url)

        pdf_links = []
        try:
            # Find all PDF links using appropriate class or tag
            pdf_links = scraper.find_all("a", href=lambda href: href and "/article/" in href)
            self._logger.info(f"PDF links found: {len(pdf_links)}")
        except Exception as e:
            self._logger.error(f"Failed to process Issue {journal.issue_url}. Error: {e}")
            self._done = False

        return pdf_links
