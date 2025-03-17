from abc import abstractmethod
from typing import List
from bs4 import ResultSet, Tag

from helper.utils import get_scraped_url_by_bs_tag
from model.base_url_publisher_models import BaseUrlPublisherSource, SourceType
from model.sql_models import ScraperFailure
from scraper.base_scraper import BaseScraper


class BaseUrlPublisherScraper(BaseScraper):
    def scrape(self) -> ResultSet | List[Tag] | None:
        """
        Scrape the source URLs of for PDF links.

        Returns:
            ResultSet | List[Tag]: A ResultSet (i.e., a list) or a list of Tag objects containing the tags to the PDF links. If no tag was found, return None.
        """
        pdf_tags = []
        for source in self._config_model.sources:
            if source.type == SourceType.JOURNAL:
                scraped_tags = self._scrape_journal(source)
            elif source.type == SourceType.ISSUE_OR_COLLECTION:
                scraped_tags = self._scrape_issue_or_collection(source)
            else:
                scraped_tag = self._scrape_article(source)
                scraped_tags = [scraped_tag] if scraped_tag is not None else None

            if scraped_tags is not None:
                pdf_tags.extend(scraped_tags)
            else:
                self._logger.warning(f"No link found in {source.url}, perhaps due to anti-bot protection.")

        return pdf_tags if pdf_tags else None

    def scrape_link(self, failure: ScraperFailure) -> List[str]:
        link = failure.source
        self._logger.info(f"Scraping URL: {link}")

        error = failure.message.lower()
        if "journal" in error:
            scraped_tags = self._scrape_journal(
                BaseUrlPublisherSource(url=link, type=str(SourceType.JOURNAL))
            )
        elif "issue" in error or "collection" in error:
            scraped_tags = self._scrape_issue_or_collection(
                BaseUrlPublisherSource(url=link, type=str(SourceType.ISSUE_OR_COLLECTION))
            )
        elif "article" in error:
            scraped_tags = self._scrape_article(
                BaseUrlPublisherSource(url=link, type=str(SourceType.ARTICLE))
            )
            scraped_tags = [scraped_tags] if scraped_tags is not None else []
        else:
            failure.message += " - issue"
            if (scraped_tags := self.scrape_link(failure)) is None:
                failure.message = failure.message.replace(" - issue", " - article")
                scraped_tags = self.scrape_link(failure)

        return self.post_process(scraped_tags) if scraped_tags is not None else []

    def post_process(self, scrape_output: ResultSet | List[Tag]) -> List[str]:
        """
        Extract the href attribute from the links.

        Args:
            scrape_output (ResultSet | List[Tag]): A ResultSet (i.e., a list) or a list of Tag objects containing the tags to the PDF links.

        Returns:
            List[str]: A list of strings containing the PDF links
        """
        return list(set([get_scraped_url_by_bs_tag(tag, self._config_model.base_url) for tag in scrape_output]))

    @abstractmethod
    def _scrape_journal(self, source: BaseUrlPublisherSource) -> ResultSet | List[Tag] | None:
        """
        Scrape all articles of a journal. This method must be implemented in the derived class.

        Args:
            source (BaseUrlPublisherSource): The journal to scrape.

        Returns:
            ResultSet | List[Tag] | None: A ResultSet (i.e., a list) or a list of Tag objects containing the PDF links. If no tag was found, return None.
        """
        pass

    @abstractmethod
    def _scrape_issue_or_collection(self, source: BaseUrlPublisherSource) -> ResultSet | List[Tag] | None:
        """
        Scrape the issue (or collection) URL for PDF links. This method must be implemented in the derived class.

        Args:
            source (BaseUrlPublisherSource): The issue / collection to scrape.

        Returns:
            ResultSet | List[Tag] | None: A ResultSet (i.e., a list) or a list of Tag objects containing the PDF links. If no tag was found, return None.
        """
        pass

    @abstractmethod
    def _scrape_article(self, source: BaseUrlPublisherSource) -> Tag | None:
        """
        Scrape a single article. This method must be implemented in the derived class.

        Args:
            source (BaseUrlPublisherSource): The article to scrape.

        Returns:
            Tag | None: The tag containing the PDF link found in the article, or None if no tag was found.
        """
        pass
