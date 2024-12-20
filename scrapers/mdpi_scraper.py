from typing import List, Type
from pydantic import BaseModel

from scrapers.base_iterative_publisher_scraper import (
    IterativePublisherScrapeOutput,
    BaseIterativePublisherScraper,
    IterativePublisherScrapeJournalOutput,
    IterativePublisherScrapeVolumeOutput,
    IterativePublisherScrapeIssueOutput,
)
from scrapers.base_scraper import BaseConfigScraper
from utils import get_scraped_urls


class MDPIJournal(BaseModel):
    url: str
    name: str
    start_volume: int | None = 1
    end_volume: int | None = 16
    start_issue: int | None = 1
    end_issue: int | None = 30


class MDPIConfig(BaseConfigScraper):
    journals: List[MDPIJournal]


class MDPIScraper(BaseIterativePublisherScraper):
    @property
    def model_class(self) -> Type[MDPIConfig]:
        """
        Return the configuration model class.

        Returns:
            Type[MDPIConfig]: The configuration model class.
        """
        return MDPIConfig

    @property
    def cookie_selector(self) -> str:
        return ""

    def scrape(self, model: MDPIConfig) -> IterativePublisherScrapeOutput:
        """
        Scrape the MDPI journals for PDF links.

        Args:
            model (MDPIConfig): The configuration model.

        Returns:
            IterativePublisherScrapeOutput: A dictionary containing the PDF links.
        """
        links = {}

        for journal in model.journals:
            links[journal.name] = self._scrape_journal(journal)

        return links

    def _scrape_journal(self, journal: MDPIJournal) -> IterativePublisherScrapeJournalOutput:
        """
        Scrape all volumes of a journal.

        Args:
            journal (MDPIJournal): The journal to scrape.

        Returns:
            IterativePublisherScrapeJournalOutput: A dictionary containing the PDF links.
        """
        self._logger.info(f"Processing Journal {journal.name}")

        start_volume = journal.start_volume
        end_volume = journal.end_volume

        start_issue = journal.start_issue
        end_issue = journal.end_issue

        journal_url = journal.url

        return {
            volume_num: self._scrape_volume(journal_url, start_issue, end_issue, volume_num)
            for volume_num in range(start_volume, end_volume + 1)
        }

    def _scrape_volume(
        self, journal_url: str, start_issue: int, end_issue: int, volume_num: int
    ) -> IterativePublisherScrapeVolumeOutput:
        """
        Scrape all issues of a volume.

        Args:
            journal_url (str): The URL of the journal.
            start_issue (int): The starting issue number.
            end_issue (int): The ending issue number.
            volume_num (int): The volume number.

        Returns:
            IterativePublisherScrapeVolumeOutput: A dictionary containing the PDF links.
        """
        self._logger.info(f"Processing Volume {volume_num}")
        return {
            issue_num: sir
            for issue_num in range(start_issue, end_issue + 1)
            if (sir := self._scrape_issue(journal_url, volume_num, issue_num))
        }

    def _scrape_issue(self, journal_url: str, volume_num: int, issue_num: int) -> IterativePublisherScrapeIssueOutput:
        """
        Scrape the issue URL for PDF links.

        Args:
            journal_url (str): The URL of the journal.
            volume_num (int): The volume number.
            issue_num (int): The issue number.

        Returns:
            IterativePublisherScrapeIssueOutput: A list of PDF links found in the issue.
        """
        base_url = "https://www.mdpi.com"
        issue_url = f"{journal_url}/{volume_num}/{issue_num}"
        self._logger.info(f"Processing Issue URL: {issue_url}")

        try:
            scraper = self._scrape_url(issue_url)

            # Get all PDF links using Selenium to scroll and handle cookie popup once
            # Now find all PDF links using the class_="UD_Listings_ArticlePDF"
            pdf_links = get_scraped_urls(scraper, base_url, href=True, class_="UD_Listings_ArticlePDF")

            self._logger.info(f"PDF links found: {len(pdf_links)}")

            # If no PDF links are found, skip to the next volume
            if not pdf_links:
                self._logger.info(
                    f"No PDF links found for Issue {issue_num} in Volume {volume_num}. Skipping to the next volume."
                )
                return None

            return pdf_links
        except Exception as e:
            self._logger.error(
                f"Failed to process Issue {issue_num} in Volume {volume_num}. Error: {e}"
            )
            self._done = False
            return None

    def _scrape_article(self, *args, **kwargs) -> str | None:
        """
        Scrape a single article.

        Returns:
            str | None: The string containing the PDF link.
        """
        pass
