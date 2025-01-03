import os
from typing import Type

from helper.utils import get_scraped_url
from model.base_iterative_publisher_models import (
    IterativePublisherScrapeJournalOutput,
    IterativePublisherScrapeVolumeOutput,
    IterativePublisherScrapeIssueOutput,
)
from model.mdpi_models import MDPIConfig, MDPIJournal
from scraper.base_iterative_publisher_scraper import BaseIterativePublisherScraper


class MDPIScraper(BaseIterativePublisherScraper):
    @property
    def config_model_type(self) -> Type[MDPIConfig]:
        """
        Return the configuration model type.

        Returns:
            Type[MDPIConfig]: The configuration model type
        """
        return MDPIConfig

    def journal_identifier(self, model: MDPIJournal) -> str:
        """
        Return the journal identifier.

        Args:
            model (MDPIJournal): The configuration model.

        Returns:
            str: The journal identifier
        """
        return model.name

    def _scrape_journal(self, journal: MDPIJournal) -> IterativePublisherScrapeJournalOutput:
        """
        Scrape all volumes of a journal.

        Args:
            journal (MDPIJournal): The journal to scrape.

        Returns:
            IterativePublisherScrapeJournalOutput: A dictionary containing the PDF links.
        """
        self._logger.info(f"Processing Journal {journal.name}")
        return self._build_journal_links(journal)

    def _scrape_volume(self, journal: MDPIJournal, volume_num: int) -> IterativePublisherScrapeVolumeOutput:
        """
        Scrape all issues of a volume.

        Args:
            journal (MDPIJournal): The journal to scrape.
            volume_num (int): The volume number.

        Returns:
            IterativePublisherScrapeVolumeOutput: A dictionary containing the PDF links.
        """
        self._logger.info(f"Processing Volume {volume_num}")
        return self._build_volume_links(journal, volume_num)

    def _scrape_issue(
        self, journal: MDPIJournal, volume_num: int, issue_num: int
    ) -> IterativePublisherScrapeIssueOutput | None:
        """
        Scrape the issue URL for PDF links.

        Args:
            journal (MDPIJournal): The journal to scrape.
            volume_num (int): The volume number.
            issue_num (int): The issue number.

        Returns:
            IterativePublisherScrapeIssueOutput | None: A list of PDF links found in the issue, or None is something went wrong.
        """
        issue_url = os.path.join(journal.url, str(volume_num), str(issue_num))
        self._logger.info(f"Processing Issue URL: {issue_url}")

        try:
            scraper = self._scrape_url(issue_url)

            # Get all PDF links using Selenium to scroll and handle cookie popup once
            # Now find all PDF links using the class_="UD_Listings_ArticlePDF"
            tags = scraper.find_all("a", class_="UD_Listings_ArticlePDF", href=True)
            pdf_links = [get_scraped_url(tag, self.base_url) for tag in tags]

            self._logger.info(f"PDF links found: {len(pdf_links)}")
            return pdf_links
        except Exception as e:
            self._logger.error(
                f"Failed to process Issue {issue_num} in Volume {volume_num}. Error: {e}"
            )
            return None

    def _scrape_article(self, *args, **kwargs) -> str | None:
        """
        Scrape a single article.

        Returns:
            str | None: The string containing the PDF link.
        """
        pass
