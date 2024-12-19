from typing import List
from bs4 import ResultSet

from scrapers.url_based_publisher_scraper import UrlBasesPublisherSource, UrlBasedPublisherScraper


class IOPScraper(UrlBasedPublisherScraper):
    @property
    def cookie_selector(self) -> str:
        return "body > div.cky-consent-container.cky-classic-bottom > div.cky-consent-bar > div > div > div.cky-notice-btn-wrapper > button.cky-btn.cky-btn-accept"

    def _scrape_journal(self, source: UrlBasesPublisherSource) -> List[ResultSet]:
        pass

    def _scrape_issue(self, source: UrlBasesPublisherSource) -> List[ResultSet]:
        """
        Scrape the issue URL for PDF links.

        Args:
            source (UrlBasesPublisherSource): The issue to scrape.

        Returns:
            List[ResultSet]: A list of ResultSet objects containing the PDF links.
        """
        self._logger.info(f"Processing Issue {source.url}")

        scraper = self._scrape_url(source.url)

        pdf_links = []
        try:
            # Find all PDF links using appropriate class or tag (if lambda returns True, it will be included in the list)
            pdf_links = scraper.find_all("a", href=lambda href: href and "/article/" in href)
            self._logger.info(f"PDF links found: {len(pdf_links)}")
        except Exception as e:
            self._logger.error(f"Failed to process Issue {source.url}. Error: {e}")
            self._done = False

        return pdf_links

    def _scrape_article(self, element: UrlBasesPublisherSource) -> ResultSet | None:
        pass