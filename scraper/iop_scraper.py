from typing import List
from bs4 import ResultSet, Tag

from scraper.base_url_publisher_scraper import BaseUrlPublisherSource, BaseUrlPublisherScraper


class IOPScraper(BaseUrlPublisherScraper):
    @property
    def cookie_selector(self) -> str:
        return "body > div.cky-consent-container.cky-classic-bottom > div.cky-consent-bar > div > div > div.cky-notice-btn-wrapper > button.cky-btn.cky-btn-accept"

    @property
    def base_url(self) -> str:
        return "https://iopscience.iop.org"

    @property
    def file_extension(self) -> str:
        """
        Return the file extension of the source files.

        Returns:
            str: The file extension of the source files
        """
        return ".pdf"

    def _scrape_journal(self, source: BaseUrlPublisherSource) -> ResultSet | List[Tag]:
        """
        Scrape all articles of a journal. This method is called when the journal_url is provided in the config.

        Args:
            source (BaseUrlPublisherSource): The journal to scrape.

        Returns:
            ResultSet | List[Tag] | None: A ResultSet (i.e., a list) or a list of Tag objects containing the PDF links. If no tag was found, return None.
        """
        pass

    def _scrape_issue(self, source: BaseUrlPublisherSource) -> ResultSet | None:
        """
        Scrape the issue URL for PDF links.

        Args:
            source (BaseUrlPublisherSource): The issue to scrape.

        Returns:
            ResultSet: A ResultSet (i.e., list) object containing the tags to the PDF links, or None if no tag was found.
        """
        self._logger.info(f"Processing Issue {source.url}")

        try:
            scraper = self._scrape_url(source.url)

            # Find all PDF links using appropriate class or tag (if lambda returns True, it will be included in the list)
            pdf_tag_list = scraper.find_all("a", href=lambda href: href and "/article/" in href and "/pdf" in href)

            self._logger.info(f"PDF links found: {len(pdf_tag_list)}")
            return pdf_tag_list
        except Exception as e:
            self._logger.error(f"Failed to process Issue {source.url}. Error: {e}")
            return None

    def _scrape_article(self, element: BaseUrlPublisherSource) -> Tag | None:
        """
        Scrape a single article.

        Args:
            element (BaseUrlPublisherSource): The article to scrape.

        Returns:
            Tag | None: The tag containing the PDF link found in the article, or None if no tag was found.
        """
        pass

    @property
    def scrape_by_selenium(self) -> bool:
        return False

    @property
    def referer_url(self) -> str:
        return "https://iopscience.iop.org"
