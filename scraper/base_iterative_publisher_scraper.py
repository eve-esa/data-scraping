from abc import ABC, abstractmethod
from typing import Dict, List, TypeAlias
from pydantic import BaseModel

from scraper.base_scraper import BaseScraper, BaseConfigScraper


IterativePublisherScrapeOutput: TypeAlias = Dict[str, Dict[int, Dict[int, List[str]]]]
IterativePublisherScrapeJournalOutput: TypeAlias = Dict[int, Dict[int, List[str]]]
IterativePublisherScrapeVolumeOutput: TypeAlias = Dict[int, List[str]]
IterativePublisherScrapeIssueOutput: TypeAlias = List[str]


class BaseIterativePublisherJournal(BaseModel):
    url: str
    name: str
    start_volume: int | None = 1
    end_volume: int | None = 30
    start_issue: int | None = 1
    end_issue: int | None = 30


class BaseIterativeWithConstraintPublisherJournal(BaseIterativePublisherJournal):
    consecutive_missing_issues_threshold: int | None = 3


class BaseIterativePublisherConfig(BaseConfigScraper):
    journals: List[BaseIterativePublisherJournal]


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

    def _build_journal_links(self, journal: BaseIterativePublisherJournal) -> IterativePublisherScrapeJournalOutput:
        return {
            volume_num: self._scrape_volume(journal, volume_num)
            for volume_num in range(journal.start_volume, journal.end_volume + 1)
        }

    def _build_volume_links(
        self, journal: BaseIterativePublisherJournal, volume_num: int
    ) -> IterativePublisherScrapeVolumeOutput:
        return {
            issue_num: scrape_issue_result
            for issue_num in range(journal.start_issue, journal.end_issue + 1)
            if (scrape_issue_result := self._scrape_issue(journal, volume_num, issue_num))
        }

    @abstractmethod
    def _scrape_journal(self, journal: BaseIterativePublisherJournal) -> IterativePublisherScrapeJournalOutput:
        """
        Scrape all volumes of a journal.

        Args:
            journal (BaseIterativePublisherJournal): The journal to scrape.

        Returns:
            IterativePublisherScrapeJournalOutput: A dictionary containing the PDF links.
        """
        pass

    @abstractmethod
    def _scrape_volume(self, journal: BaseIterativePublisherJournal, volume_num: int) -> IterativePublisherScrapeVolumeOutput:
        """
        Scrape all issues of a volume.

        Args:
            journal (BaseIterativePublisherJournal): The journal to scrape.
            volume_num (int): The volume number.

        Returns:
            IterativePublisherScrapeVolumeOutput: A dictionary containing the PDF links.
        """
        pass

    @abstractmethod
    def _scrape_issue(
        self, journal: BaseIterativePublisherJournal, volume_num: int, issue_num: int
    ) -> IterativePublisherScrapeIssueOutput | None:
        """
        Scrape the issue URL for PDF links.

        Args:
            journal (BaseIterativePublisherJournal): The journal to scrape.
            volume_num (int): The volume number.
            issue_num (int): The issue number.

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


class BaseIterativeWithConstraintPublisherScraper(BaseIterativePublisherScraper, ABC):
    def __init__(self):
        super().__init__()

        self.__all_issues_missing = 0  # Track if all issues are missing for the volume

    def _build_journal_links(self, journal: BaseIterativeWithConstraintPublisherJournal):
        links = {}
        for volume_num in range(journal.start_volume, journal.end_volume + 1):
            self.__all_issues_missing = 0

            res = self._scrape_volume(journal, volume_num)

            if self.__all_issues_missing == journal.end_issue - journal.start_issue + 1:
                self._logger.warning(f"No issues found for Volume {volume_num}. Moving to next journal.")
                break  # Exit loop and move to the next journal

            links[volume_num] = res

        return links

    def _build_volume_links(
        self, journal: BaseIterativeWithConstraintPublisherJournal, volume_num: int
    ) -> IterativePublisherScrapeVolumeOutput:
        missing_issue_count = 0  # Track consecutive missing issues
        links = {}

        # Iterate over each issue in the specified range
        for issue_num in range(journal.start_issue, journal.end_issue + 1):
            res = self._scrape_issue(journal, volume_num, issue_num)
            if res:
                missing_issue_count = 0
                links[issue_num] = res
            else:
                missing_issue_count += 1
                self.__all_issues_missing += 1

            if missing_issue_count >= journal.consecutive_missing_issues_threshold:
                self._logger.warning(f"Consecutive missing issues for Volume {volume_num}. Moving to the next volume.")
                break  # Exit loop and move to the next volume

        return links