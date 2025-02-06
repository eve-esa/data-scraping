from typing import List, Type
from bs4 import Tag, ResultSet

from model.base_url_publisher_models import BaseUrlPublisherSource, BaseUrlPublisherConfig
from scraper.base_url_publisher_scraper import BaseUrlPublisherScraper


class EOSScraper(BaseUrlPublisherScraper):
    @property
    def config_model_type(self) -> Type[BaseUrlPublisherConfig]:
        """
        Return the configuration model type.

        Returns:
            Type[BaseUrlPublisherConfig]: The configuration model type
        """
        return BaseUrlPublisherConfig

    def _scrape_journal(self, source: BaseUrlPublisherSource) -> ResultSet | List[Tag] | None:
        """
        Scrape all articles of a journal.

        Args:
            source (BaseUrlPublisherSource): The journal to scrape.

        Returns:
            List[Tag] | None: A list of Tag objects containing the PDF links. If no tag was found, return None.
        """
        pass

    def _scrape_issue_or_collection(self, source: BaseUrlPublisherSource) -> ResultSet | None:
        """
        Scrape the issue (or collection) URL for PDF links.

        Args:
            source (BaseUrlPublisherSource): The issue / collection to scrape.

        Returns:
            ResultSet | None: A Result (i.e., a list) of Tag objects containing the tags to the PDF links, or None if no tag was found.
        """
        self._logger.info(f"Processing Issue / Collection {source.url}")

        try:
            scraper, driver = self._scrape_url(source.url)
            driver.quit()

            # Find all PDF links using appropriate class or tag (if lambda returns True, it will be included in the list)
            if not (pdf_tag_list := scraper.find_all(
                "a",
                href=lambda href: href and "/wp-content/uploads/" in href and ".pdf" in href,
                class_=lambda class_: class_ and "wp-element-button" in class_,
            )):
                self._save_failure(source.url)

            self._logger.debug(f"PDF links found: {len(pdf_tag_list)}")
            return pdf_tag_list
        except Exception as e:
            self._log_and_save_failure(source.url, f"Failed to process Issue {source.url}. Error: {e}")
            return None

    def _scrape_article(self, source: BaseUrlPublisherSource) -> Tag | None:
        """
        Scrape a single article.

        Args:
            source (BaseUrlPublisherSource): The article to scrape.

        Returns:
            Tag | None: The tag containing the PDF link found in the article, or None if no tag was found.
        """
        pass
