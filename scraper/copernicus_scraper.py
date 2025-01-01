import os
from typing import Type

from model.base_iterative_publisher_models import (
    BaseIterativeWithConstraintPublisherJournal,
    IterativePublisherScrapeJournalOutput,
    IterativePublisherScrapeVolumeOutput,
    IterativePublisherScrapeIssueOutput,
)
from model.copernicus_models import CopernicusConfig
from scraper.base_iterative_publisher_scraper import BaseIterativeWithConstraintPublisherScraper
from utils import get_scraped_url


class CopernicusScraper(BaseIterativeWithConstraintPublisherScraper):
    @property
    def config_model_type(self) -> Type[CopernicusConfig]:
        """
        Return the configuration model type.

        Returns:
            Type[CopernicusConfig]: The configuration model type
        """
        return CopernicusConfig

    def journal_identifier(self, model: BaseIterativeWithConstraintPublisherJournal) -> str:
        """
        Return the journal identifier.

        Args:
            model (BaseIterativeWithConstraintPublisherJournal): The configuration model.

        Returns:
            str: The journal identifier
        """
        return model.name

    def _scrape_journal(
        self, journal: BaseIterativeWithConstraintPublisherJournal
    ) -> IterativePublisherScrapeJournalOutput:
        """
        Scrape all volumes of a journal.

        Args:
            journal (BaseIterativeWithConstraintPublisherJournal): The journal to scrape.

        Returns:
            IterativePublisherScrapeJournalOutput: A dictionary containing the PDF links.
        """
        self._logger.info(f"Processing Journal {journal.name}")
        return self._build_journal_links(journal)

    def _scrape_volume(
        self, journal: BaseIterativeWithConstraintPublisherJournal, volume_num: int
    ) -> IterativePublisherScrapeVolumeOutput:
        """
        Scrape all issues of a volume.

        Args:
            journal (BaseIterativeWithConstraintPublisherJournal): The journal to scrape.
            volume_num (int): The volume number.

        Returns:
            IterativePublisherScrapeVolumeOutput: A dictionary containing the PDF links.
        """
        self._logger.info(f"Processing Volume {volume_num}")
        return self._build_volume_links(journal, volume_num)

    def _scrape_issue(
        self, journal: BaseIterativeWithConstraintPublisherJournal, volume_num: int, issue_num: int
    ) -> IterativePublisherScrapeIssueOutput | None:
        """
        Scrape the issue URL for PDF links.

        Args:
            journal (BaseIterativeWithConstraintPublisherJournal): The journal to scrape.
            volume_num (int): The volume number.
            issue_num (int): The issue number.

        Returns:
            IterativePublisherScrapeIssueOutput | None: A list of PDF links found in the issue, or None is something went wrong.
        """
        issue_url = os.path.join(journal.url, "articles", str(volume_num), f"issue{issue_num}.html")
        self._logger.info(f"Processing Issue URL: {issue_url}")

        try:
            scraper = self._scrape_url(issue_url)

            # find all the URLs to the articles where I can grab the PDF links (one per article URL, if lambda returns
            # True, it will be included in the list)
            tags = scraper.find_all("a", class_="article-title", href=lambda href: href and "/articles/" in href)

            pdf_links = [
                pdf_link
                for pdf_link in map(lambda tag: self._scrape_article(get_scraped_url(tag, journal.url), journal.url), tags)
                if pdf_link
            ]

            self._logger.info(f"PDF links found: {len(pdf_links)}")
            return pdf_links
        except Exception as e:
            self._logger.error(f"Failed to process Issue {issue_num} in Volume {volume_num}. Error: {e}")
            return None

    def _scrape_article(self, article_url: str, base_url: str) -> str | None:
        """
        Scrape a single article.

        Args:
            article_url (str): The article links to scrape.
            base_url (str): The base URL.

        Returns:
            str | None: The string containing the PDF link.
        """
        self._logger.info(f"Processing Article URL: {article_url}")

        try:
            scraper = self._scrape_url(article_url)

            # Find all PDF links using appropriate class or tag (if lambda returns True, it will be included in the list)
            pdf_tag = scraper.find("a", href=lambda href: href and ".pdf" in href)
            if pdf_tag:
                return get_scraped_url(pdf_tag, base_url)

            return None
        except Exception as e:
            self._logger.error(f"Failed to process Article {article_url}. Error: {e}")
            return None
