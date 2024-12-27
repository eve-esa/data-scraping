from abc import abstractmethod
from typing import Dict, List, TypeAlias
from pydantic import BaseModel

from scraper.base_scraper import BaseScraper, BaseConfigScraper


IterativePublisherScrapeOutput: TypeAlias = Dict[str, Dict[int, Dict[int, List[str]]]]
IterativePublisherScrapeJournalOutput: TypeAlias = Dict[int, Dict[int, List[str]]]
IterativePublisherScrapeVolumeOutput: TypeAlias = Dict[int, List[str]]
IterativePublisherScrapeIssueOutput: TypeAlias = List[str]


class BaseIterativePublisherConfig(BaseConfigScraper):
    journals: List


class BaseIterativePublisherScraper(BaseScraper):
    def scrape(self, model: BaseIterativePublisherConfig) -> IterativePublisherScrapeOutput | None:
        """
        Scrape the journals for PDF links.

        Args:
            model (BaseIterativePublisherConfig): The configuration model.

        Returns:
            IterativePublisherScrapeOutput | None: A dictionary containing the PDF links, or None if no link was found.
        """
        links = {}

        for journal in model.journals:
            if scraped_tags := self._scrape_journal(journal):
                links[self.journal_identifier(journal)] = scraped_tags

        return links if links else None

    def post_process(self, scrape_output: IterativePublisherScrapeOutput) -> List[str]:
        """
        Extract the PDF links from the dictionary.

        Args:
            scrape_output: A dictionary containing the PDF links.

        Returns:
            List[str]: A list of strings containing the PDF links
        """
        return [
            issue_link
            for journal_links in scrape_output.values()
            for volume_links in journal_links.values()
            for issues_links in volume_links.values()
            for issue_link in issues_links
        ]

    @abstractmethod
    def _scrape_journal(self, journal: BaseConfigScraper) -> IterativePublisherScrapeJournalOutput:
        """
        Scrape all volumes of a journal.

        Args:
            journal (BaseConfigScraper): The journal to scrape.

        Returns:
            IterativePublisherScrapeJournalOutput: A dictionary containing the PDF links.
        """
        pass

    @abstractmethod
    def _scrape_volume(self, *args, **kwargs) -> IterativePublisherScrapeVolumeOutput:
        """
        Scrape all issues of a volume.

        Returns:
            IterativePublisherScrapeVolumeOutput: A dictionary containing the PDF links.
        """
        pass

    @abstractmethod
    def _scrape_issue(self, *args, **kwargs) -> IterativePublisherScrapeIssueOutput | None:
        """
        Scrape the issue URL for PDF links.

        Returns:
            IterativePublisherScrapeIssueOutput | None: A list of PDF links found in the issue, or None is something went wrong.
        """
        pass

    @abstractmethod
    def _scrape_article(self, *args, **kwargs) -> str | None:
        """
        Scrape a single article.

        Returns:
            str | None: The string containing the PDF link.
        """
        pass

    @abstractmethod
    def journal_identifier(self, model: BaseModel) -> str:
        """
        Return the journal identifier.

        Args:
            model (BaseModel): The configuration model.

        Returns:
            str: The journal identifier
        """
        pass
