from typing import List, Type, Tuple
from pydantic import BaseModel

from scrapers.base_iterative_publisher_scraper import (
    BaseIterativePublisherScraper,
    IterativePublisherScrapeJournalOutput,
    IterativePublisherScrapeVolumeOutput,
    IterativePublisherScrapeIssueOutput,
    IterativePublisherScrapeOutput,
)
from scrapers.base_scraper import BaseConfigScraper
from utils import get_scraped_urls


class CopernicusJournal(BaseModel):
    url: str
    name: str
    start_volume: int | None = 1
    end_volume: int | None = 30
    start_issue: int | None = 1
    end_issue: int | None = 30
    consecutive_missing_volumes_threshold: int | None = 3
    consecutive_missing_issues_threshold: int | None = 3


class CopernicusConfig(BaseConfigScraper):
    journals: List[CopernicusJournal]


class CopernicusScraper(BaseIterativePublisherScraper):
    @property
    def model_class(self) -> Type[CopernicusConfig]:
        """
        Return the configuration model class.

        Returns:
            Type[CopernicusConfig]: The configuration model class.
        """
        return CopernicusConfig

    @property
    def cookie_selector(self) -> str:
        return ""

    def scrape(self, model: CopernicusConfig) -> IterativePublisherScrapeOutput:
        """
        Scrape the AMS journals for PDF links.

        Args:
            model (CopernicusConfig): The configuration model.

        Returns:
            IterativePublisherScrapeOutput: A dictionary containing the PDF links.
        """
        links = {}

        for journal in model.journals:
            res = self._scrape_journal(journal)
            if res:
                links[journal.name] = res

        return links

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
            res, all_issues_missing = self._scrape_volume(
                journal_url, start_issue, end_issue, volume_num, consecutive_missing_issues_threshold
            )

            if all_issues_missing == end_issue - start_issue + 1:
                self._logger.warning(f"No issues found for Volume {volume_num}. Moving to next journal.")
                self._done = True
                break  # Exit loop and move to the next journal

            links[volume_num] = res

        return links

    def _scrape_volume(
        self, journal_url: str, start_issue: int, end_issue: int, volume_num: int, consecutive_missing_issues_threshold: int
    ) -> Tuple[IterativePublisherScrapeVolumeOutput, int]:
        """
        Scrape all issues of a volume.

        Args:
            journal_url (str): The URL of the journal.
            start_issue (int): The starting issue number.
            end_issue (int): The ending issue number.
            volume_num (int): The volume number.
            consecutive_missing_issues_threshold (int): The number of consecutive missing issues to allow before moving
                to the next volume.

        Returns:
            Tuple[IterativePublisherScrapeVolumeOutput, int]: A dictionary containing the PDF links, and the number of
                missing issues.
        """
        self._logger.info(f"Processing Volume {volume_num}")

        missing_issue_count = 0  # Track consecutive missing issues
        all_issues_missing = 0  # Track if all issues are missing for the volume

        links = {}

        # Iterate over each issue in the specified range
        for issue_num in range(start_issue, end_issue + 1):
            res = self._scrape_issue(journal_url, volume_num, issue_num)
            if res:
                missing_issue_count = 0
                links[issue_num] = res
            else:
                missing_issue_count += 1
                all_issues_missing += 1

            if missing_issue_count >= consecutive_missing_issues_threshold:
                self._logger.warning(f"Consecutive missing issues for Volume {volume_num}. Moving to the next volume.")
                self._done = True
                break  # Exit loop and move to the next volume

        return links, all_issues_missing

    def _scrape_issue(self, journal_url: str, volume_num: int, issue_num: int) -> IterativePublisherScrapeIssueOutput:
        """
        Scrape the issue URL for PDF links.

        Args:
            journal_url (str): The journal code.
            volume_num (int): The volume number.
            issue_num (int): The issue number.

        Returns:
            IterativePublisherScrapeIssueOutput: A list of PDF links found in the issue.
        """
        issue_url = f"{journal_url}/articles/{volume_num}/issue{issue_num}.html"
        self._logger.info(f"Processing Issue URL: {issue_url}")

        try:
            scraper = self._scrape_url(issue_url)

            # find all the URLs to the articles where I can grab the PDF links (one per article URL, if lambda returns
            # True, it will be included in the list)
            article_urls = get_scraped_urls(
                scraper,
                journal_url,
                href=lambda href: href and f"/articles/" in href,
                class_="article-title",
            )

            pdf_links = [self._scrape_article(article_url, journal_url) for article_url in article_urls]
            pdf_links = [link for link in pdf_links if link]

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
                return base_url + pdf_tag.get("href") if pdf_tag.get("href").startswith("/") else pdf_tag.get("href")

            return None
        except Exception as e:
            self._logger.error(f"Failed to process Article {article_url}. Error: {e}")
            return None
