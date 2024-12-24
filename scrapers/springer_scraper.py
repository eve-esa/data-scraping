from typing import List
from bs4 import ResultSet, Tag

from scrapers.base_url_publisher_scraper import BaseUrlPublisherSource, BaseUrlPublisherScraper, SourceType


class SpringerScraper(BaseUrlPublisherScraper):
    @property
    def cookie_selector(self) -> str:
        return "button.cc-banner__button-accept"

    @property
    def base_url(self) -> str:
        return "https://link.springer.com"

    def _scrape_journal(self, source: BaseUrlPublisherSource) -> List[Tag] | None:
        """
        Scrape all articles of a journal. This method is called when the journal_url is provided in the config.

        Args:
            source (BaseUrlPublisherSource): The journal to scrape.

        Returns:
            List[Tag] | None: A list of Tag objects containing the PDF links. If no tag was found, return None.
        """
        self._logger.info(f"Processing Journal {source.url}")

        # navigate through the pagination of the journal
        counter = 1
        article_tag_list = []
        while True:
            try:
                scraper = self._scrape_url(f"{source.url}?filterOpenAccess=false&page={counter}")

                # Find all PDF links using appropriate class or tag (if lambda returns True, it will be included in the list)
                tags = scraper.find_all("a", href=lambda href: href and "/article/" in href)
                if len(tags) == 0:
                    break

                article_tag_list.extend(tags)
                counter += 1
            except Exception as e:
                self._logger.error(f"Failed to process Journal {source.url}. Error: {e}")
                break

        try:
            # For each tag of articles previously collected, scrape the article
            pdf_tag_list = [
                self._scrape_article(BaseUrlPublisherSource(url=tag.get("href"), type=str(SourceType.ARTICLE)))
                for tag in article_tag_list
            ]
            pdf_tag_list = [tag for tag in pdf_tag_list if tag]
            self._logger.info(f"PDF links found: {pdf_tag_list}")

            return pdf_tag_list
        except Exception as e:
            self._logger.error(f"Failed to process Journal {source.url}. Error: {e}")
            return None

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
            pdf_tag_list = scraper.find_all("a", href=lambda href: href and "/pdf/" in href)
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
            scraper = self._scrape_url(source.url)

            # Find the PDF link using appropriate class or tag (if lambda returns True, it will be included in the list)
            return scraper.find("a", href=lambda href: href and "/pdf/" in href)
        except Exception as e:
            self._logger.error(f"Failed to process Article {source.url}. Error: {e}")
            return None
