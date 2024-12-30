from typing import List
from bs4 import Tag, ResultSet

from model.base_url_publisher_models import BaseUrlPublisherSource, SourceType
from scraper.base_url_publisher_scraper import BaseUrlPublisherScraper
from utils import get_scraped_url


class FrontiersScraper(BaseUrlPublisherScraper):
    def _scrape_journal(self, source: BaseUrlPublisherSource) -> ResultSet | List[Tag] | None:
        """
        Scrape all articles of a journal.

        Args:
            source (BaseUrlPublisherSource): The journal to scrape.

        Returns:
            ResultSet | List[Tag] | None: A ResultSet (i.e., a list) or a list of Tag objects containing the PDF links. If no tag was found, return None.
        """
        pass

    def _scrape_issue_or_collection(self, source: BaseUrlPublisherSource) -> List[Tag] | None:
        """
        Scrape the issue (or collection) URL for PDF links.

        Args:
            source (BaseUrlPublisherSource): The issue / collection to scrape.

        Returns:
            List[Tag] | None: A list of Tag objects containing the tags to the PDF links, or None if no tag was found.
        """
        self._logger.info(f"Processing Issue / Collection {source.url}")

        try:
            scraper = self._scrape_url_by_bs4(source.url)

            # Find all PDF links using appropriate class or tag (if lambda returns True, it will be included in the list)
            article_tag_list = scraper.find_all(
                "a", href=lambda href: href and "/articles/" in href and "full" in href, class_="CardArticle__wrapper"
            )

            # For each tag of articles previously collected, scrape the article
            pdf_tag_list = [
                tag for tag in (
                    self._scrape_article(
                        BaseUrlPublisherSource(url=get_scraped_url(tag, self.base_url), type=str(SourceType.ARTICLE))
                    )
                    for tag in article_tag_list
                ) if tag
            ]
            self._logger.info(f"PDF links found: {len(pdf_tag_list)}")

            return pdf_tag_list
        except Exception as e:
            self._logger.error(f"Failed to process Issue {source.url}. Error: {e}")
            return None

    def _scrape_article(self, source: BaseUrlPublisherSource) -> Tag | None:
        """
        Scrape a single article.

        Args:
            source (BaseUrlPublisherSource): The article to scrape.

        Returns:
            Tag | None: The tag containing the PDF link found in the article, or None if no tag was found.
        """
        self._logger.info(f"Processing Article {source.url}")

        try:
            scraper = self._scrape_url_by_bs4(source.url)

            # Find the PDF link using appropriate class or tag (if lambda returns True, it will be included in the list)
            return scraper.find("a", href=lambda href: href and "/pdf" in href, class_="ActionsDropDown__option")
        except Exception as e:
            self._logger.error(f"Failed to process Article {source.url}. Error: {e}")
            return None
