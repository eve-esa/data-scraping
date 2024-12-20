from typing import List
from bs4 import ResultSet, Tag

from scrapers.url_based_publisher_scraper import UrlBasesPublisherSource, UrlBasedPublisherScraper


class IOPScraper(UrlBasedPublisherScraper):
    @property
    def cookie_selector(self) -> str:
        return "body > div.cky-consent-container.cky-classic-bottom > div.cky-consent-bar > div > div > div.cky-notice-btn-wrapper > button.cky-btn.cky-btn-accept"

    def _scrape_journal(self, source: UrlBasesPublisherSource) -> ResultSet | List[Tag]:
        """
        Scrape all articles of a journal. This method is called when the journal_url is provided in the config.

        Args:
            source (UrlBasesPublisherSource): The journal to scrape.

        Returns:
            ResultSet | List[Tag]: A ResultSet (i.e., a list) or a list of Tag objects containing the PDF links.
        """
        pass

    def _scrape_issue(self, source: UrlBasesPublisherSource) -> ResultSet:
        """
        Scrape the issue URL for PDF links.

        Args:
            source (UrlBasesPublisherSource): The issue to scrape.

        Returns:
            ResultSet: A ResultSet (i.e., list) object containing the tags to the PDF links.
        """
        self._logger.info(f"Processing Issue {source.url}")

        try:
            scraper = self._scrape_url(source.url)

            # Find all PDF links using appropriate class or tag (if lambda returns True, it will be included in the list)
            pdf_tag_list = scraper.find_all("a", href=lambda href: href and "/article/" in href)
            self._logger.info(f"PDF links found: {len(pdf_tag_list)}")
        except Exception as e:
            self._logger.error(f"Failed to process Issue {source.url}. Error: {e}")
            self._done = False

            pdf_tag_list = []

        return pdf_tag_list

    def _scrape_article(self, element: UrlBasesPublisherSource) -> Tag | None:
        """
        Scrape a single article.

        Args:
            element (UrlBasesPublisherSource): The article to scrape.

        Returns:
            Tag | None: The tag containing the PDF link found in the article, or None if no tag was found.
        """
        pass
