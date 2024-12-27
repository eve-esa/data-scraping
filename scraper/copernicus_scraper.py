import os
from typing import List, Type
from pydantic import BaseModel

from scraper.base_iterative_publisher_scraper import (
    BaseIterativePublisherScraper,
    IterativePublisherScrapeJournalOutput,
    IterativePublisherScrapeVolumeOutput,
    IterativePublisherScrapeIssueOutput,
    BaseIterativePublisherConfig,
)
from utils import get_scraped_url


class CopernicusJournal(BaseModel):
    url: str
    name: str
    start_volume: int | None = 1
    end_volume: int | None = 30
    start_issue: int | None = 1
    end_issue: int | None = 30
    consecutive_missing_volumes_threshold: int | None = 3
    consecutive_missing_issues_threshold: int | None = 3


class CopernicusConfig(BaseIterativePublisherConfig):
    journals: List[CopernicusJournal]


class CopernicusScraper(BaseIterativePublisherScraper):
    def __init__(self):
        super().__init__()

        self.__all_issues_missing = 0  # Track if all issues are missing for the volume

    @property
    def config_model_type(self) -> Type[CopernicusConfig]:
        """
        Return the configuration model type.

        Returns:
            Type[CopernicusConfig]: The configuration model type
        """
        return CopernicusConfig

    @property
    def cookie_selector(self) -> str:
        return ""

    @property
    def base_url(self) -> str:
        return ""

    def journal_identifier(self, model: CopernicusJournal) -> str:
        """
        Return the journal identifier.

        Args:
            model (CopernicusJournal): The configuration model.

        Returns:
            str: The journal identifier
        """
        return model.name

    def _scrape_journal(self, journal: CopernicusJournal) -> IterativePublisherScrapeJournalOutput:
        """
        Scrape all volumes of a journal.

        Args:
            journal (CopernicusJournal): The journal to scrape.

        Returns:
            IterativePublisherScrapeJournalOutput: A dictionary containing the PDF links.
        """
        self._logger.info(f"Processing Journal {journal.name}")

        start_volume = journal.start_volume
        end_volume = journal.end_volume

        start_issue = journal.start_issue
        end_issue = journal.end_issue

        journal_url = journal.url

        consecutive_missing_issues_threshold = journal.consecutive_missing_issues_threshold

        links = {}
        for volume_num in range(start_volume, end_volume + 1):
            self.__all_issues_missing = 0

            res = self._scrape_volume(
                journal_url, start_issue, end_issue, volume_num, consecutive_missing_issues_threshold
            )

            if self.__all_issues_missing == end_issue - start_issue + 1:
                self._logger.warning(f"No issues found for Volume {volume_num}. Moving to next journal.")
                break  # Exit loop and move to the next journal

            links[volume_num] = res

        return links

    def _scrape_volume(
        self,
        journal_url: str,
        start_issue: int,
        end_issue: int,
        volume_num: int,
        consecutive_missing_issues_threshold: int,
    ) -> IterativePublisherScrapeVolumeOutput:
        """
        Scrape all issues of a volume.

        Args:
            journal_url (str): The URL of the journal.
            start_issue (int): The starting issue number.
            end_issue (int): The ending issue number.
            volume_num (int): The volume number.
            consecutive_missing_issues_threshold (int): The number of consecutive missing issues to allow before moving to the next volume.

        Returns:
            IterativePublisherScrapeVolumeOutput: A dictionary containing the PDF links.
        """
        self._logger.info(f"Processing Volume {volume_num}")

        missing_issue_count = 0  # Track consecutive missing issues
        links = {}

        # Iterate over each issue in the specified range
        for issue_num in range(start_issue, end_issue + 1):
            res = self._scrape_issue(journal_url, volume_num, issue_num)
            if res:
                missing_issue_count = 0
                links[issue_num] = res
            else:
                missing_issue_count += 1
                self.__all_issues_missing += 1

            if missing_issue_count >= consecutive_missing_issues_threshold:
                self._logger.warning(f"Consecutive missing issues for Volume {volume_num}. Moving to the next volume.")
                break  # Exit loop and move to the next volume

        return links

    def _scrape_issue(
        self, journal_url: str, volume_num: int, issue_num: int
    ) -> IterativePublisherScrapeIssueOutput | None:
        """
        Scrape the issue URL for PDF links.

        Args:
            journal_url (str): The journal code.
            volume_num (int): The volume number.
            issue_num (int): The issue number.

        Returns:
            IterativePublisherScrapeIssueOutput | None: A list of PDF links found in the issue, or None is something went wrong.
        """
        issue_url = os.path.join(journal_url, "articles", str(volume_num), f"issue{issue_num}.html")
        self._logger.info(f"Processing Issue URL: {issue_url}")

        try:
            scraper = self._scrape_url(issue_url)

            # find all the URLs to the articles where I can grab the PDF links (one per article URL, if lambda returns
            # True, it will be included in the list)
            tags = scraper.find_all("a", class_="article-title", href=lambda href: href and "/articles/" in href)

            pdf_links = [
                pdf_link
                for pdf_link in map(lambda tag: self._scrape_article(get_scraped_url(tag, journal_url), journal_url), tags)
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
