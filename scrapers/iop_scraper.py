from typing import List
from bs4 import ResultSet

from scrapers.base_publisher_scraper import BasePublisherSource, BasePublisherScraper


class IOPScraper(BasePublisherScraper):
    @property
    def cookie_selector(self) -> str:
        return "body > div.cky-consent-container.cky-classic-bottom > div.cky-consent-bar > div > div > div.cky-notice-btn-wrapper > button.cky-btn.cky-btn-accept"

    def _scrape_journal(self, source: BasePublisherSource) -> List[ResultSet]:
        pass

    def _scrape_issue(self, source: BasePublisherSource) -> List[ResultSet]:
        """
        Scrape the issue URL for PDF links.

        Args:
            source (BasePublisherSource): The issue to scrape.

        Returns:
            List[ResultSet]: A list of ResultSet objects containing the PDF links.
        """
        self._logger.info(f"Processing Issue {source.url}")

        scraper = self._setup_scraper(source.url)

        pdf_links = []
        try:
            # Find all PDF links using appropriate class or tag
            pdf_links = scraper.find_all("a", href=lambda href: href and "/article/" in href)
            self._logger.info(f"PDF links found: {len(pdf_links)}")
        except Exception as e:
            self._logger.error(f"Failed to process Issue {source.url}. Error: {e}")
            self._done = False

        return pdf_links

    def _scrape_article(self, element: BasePublisherSource) -> ResultSet | None:
        pass