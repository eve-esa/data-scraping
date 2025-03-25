from abc import ABC, abstractmethod
from typing import List

from model.base_iterative_publisher_models import (
    BaseIterativePublisherJournal,
    BaseIterativeWithConstraintPublisherJournal,
    IterativePublisherScrapeJournalOutput,
    IterativePublisherScrapeVolumeOutput,
    IterativePublisherScrapeIssueOutput,
    IterativePublisherScrapeOutput,
)
from scraper.base_scraper import BaseScraper


class BaseIterativePublisherScraper(BaseScraper):
    def scrape(self) -> IterativePublisherScrapeOutput | None:
        """
        Scrape the journals for PDF links.

        Returns:
            IterativePublisherScrapeOutput | None: A dictionary containing the PDF links, or None if no link was found.
        """
        links = {}

        for journal in self._config_model.journals:
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
        return list(set([
            issue_link
            for journal_links in scrape_output.values()
            for volume_links in journal_links.values()
            for issues_links in volume_links.values()
            for issue_link in issues_links
        ]))

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

    def _scrape_journal(self, journal: BaseIterativePublisherJournal) -> IterativePublisherScrapeJournalOutput:
        """
        Scrape all volumes of a journal. This method must be implemented in the derived class.

        Args:
            journal (BaseIterativePublisherJournal): The journal to scrape.

        Returns:
            IterativePublisherScrapeJournalOutput: A dictionary containing the PDF links.
        """
        self._logger.info(f"Processing Journal {journal.name}")
        return self._build_journal_links(journal)

    def _scrape_volume(
        self, journal: BaseIterativePublisherJournal, volume_num: int
    ) -> IterativePublisherScrapeVolumeOutput:
        """
        Scrape all issues of a volume. This method must be implemented in the derived class.

        Args:
            journal (BaseIterativePublisherJournal): The journal to scrape.
            volume_num (int): The volume number.

        Returns:
            IterativePublisherScrapeVolumeOutput: A dictionary containing the PDF links.
        """
        self._logger.info(f"Processing Volume {volume_num}")
        return self._build_volume_links(journal, volume_num)

    @abstractmethod
    def _scrape_issue(
        self, journal: BaseIterativePublisherJournal, volume_num: int, issue_num: int
    ) -> IterativePublisherScrapeIssueOutput | None:
        """
        Scrape the issue URL for PDF links. This method must be implemented in the derived class.

        Args:
            journal (BaseIterativePublisherJournal): The journal to scrape.
            volume_num (int): The volume number.
            issue_num (int): The issue number.

        Returns:
            IterativePublisherScrapeIssueOutput | None: A list of PDF links found in the issue, or None if something went wrong.
        """
        pass

    @abstractmethod
    def _scrape_article(self, article_url: str) -> str | None:
        """
        Scrape a single article.

        Args:
            article_url (str): The article links to scrape.

        Returns:
            str | None: The string containing the PDF link.
        """
        pass

    @abstractmethod
    def journal_identifier(self, model: BaseIterativePublisherJournal) -> str:
        """
        Return the journal identifier. This method must be implemented in the derived class.

        Args:
            model (BaseIterativePublisherJournal): The configuration model.

        Returns:
            str: The journal identifier
        """
        pass


class BaseIterativeWithConstraintPublisherScraper(BaseIterativePublisherScraper, ABC):
    def _build_journal_links(self, journal: BaseIterativeWithConstraintPublisherJournal):
        missing_volume_count = 0  # Track consecutive missing volumes
        links = {}

        # Iterate over each volume in the specified range
        for volume_num in range(journal.start_volume, journal.end_volume + 1):
            if missing_volume_count >= journal.consecutive_missing_volumes_threshold:
                self._logger.warning(f"Max consecutive missing volumes for Journal {journal.name} reached. Moving to the next journal.")
                break  # Exit loop and move to the next journal

            if res := self._scrape_volume(journal, volume_num):
                missing_volume_count = 0
                links[volume_num] = res
                continue

            missing_volume_count += 1

        return links

    def _build_volume_links(
        self, journal: BaseIterativeWithConstraintPublisherJournal, volume_num: int
    ) -> IterativePublisherScrapeVolumeOutput:
        missing_issue_count = 0  # Track consecutive missing issues
        links = {}

        # Iterate over each issue in the specified range
        for issue_num in range(journal.start_issue, journal.end_issue + 1):
            if missing_issue_count >= journal.consecutive_missing_issues_threshold:
                self._logger.warning(f"Max consecutive missing issues for Volume {volume_num} reached. Moving to the next volume.")
                break  # Exit loop and move to the next volume

            res = self._scrape_issue(journal, volume_num, issue_num)
            if self._has_valid_results_from_issue(res):
                missing_issue_count = 0
                links[issue_num] = res
                continue

            missing_issue_count += 1

        return links

    def _has_valid_results_from_issue(self, results: IterativePublisherScrapeIssueOutput | None) -> bool:
        return bool(results)
