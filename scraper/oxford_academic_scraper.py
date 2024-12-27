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


class OxfordAcademicJournal(BaseModel):
    url: str
    name: str
    code: str
    start_volume: int
    end_volume: int
    start_issue: int
    end_issue: int


class OxfordAcademicConfig(BaseIterativePublisherConfig):
    journals: List[OxfordAcademicJournal]


class OxfordAcademicScraper(BaseIterativePublisherScraper):
    @property
    def config_model_type(self) -> Type[OxfordAcademicConfig]:
        """
        Return the configuration model type.

        Returns:
            Type[OxfordAcademicConfig]: The configuration model type
        """
        return OxfordAcademicConfig

    @property
    def cookie_selector(self) -> str:
        return "[id='accept-button']"

    @property
    def base_url(self) -> str:
        return "https://academic.oup.com"

    def journal_identifier(self, model: OxfordAcademicJournal) -> str:
        """
        Return the journal identifier.

        Args:
            model (OxfordAcademicJournal): The configuration model.

        Returns:
            str: The journal identifier
        """
        return model.code

    def _scrape_journal(self, journal: OxfordAcademicJournal) -> IterativePublisherScrapeJournalOutput:
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

        journal_code = journal.code

        return {
            volume_num: self._scrape_volume(journal_code, start_issue, end_issue, volume_num)
            for volume_num in range(start_volume, end_volume + 1)
        }

    def _scrape_volume(
        self, journal_code: str, start_issue: int, end_issue: int, volume_num: int,
    ) -> IterativePublisherScrapeVolumeOutput:
        """
        Scrape all issues of a volume.

        Args:
            journal_code (str): The journal code.
            start_issue (int): The starting issue number.
            end_issue (int): The ending issue number.
            volume_num (int): The volume number.

        Returns:
            IterativePublisherScrapeVolumeOutput: A dictionary containing the PDF links.
        """
        self._logger.info(f"Processing Volume {volume_num}")
        return {
            issue_num: scrape_issue_result
            for issue_num in range(start_issue, end_issue + 1)
            if (scrape_issue_result := self._scrape_issue(journal_code, volume_num, issue_num))
        }

    def _scrape_issue(
        self, journal_code: str, volume_num: int, issue_num: int
    ) -> IterativePublisherScrapeIssueOutput | None:
        """
        Scrape the issue URL for PDF links.

        Args:
            journal_code (str): The journal code.
            volume_num (int): The volume number.
            issue_num (int): The issue number.

        Returns:
            IterativePublisherScrapeIssueOutput | None: A list of PDF links found in the issue, or None is something went wrong.
        """
        issue_url = os.path.join(self.base_url, journal_code, "issue", str(volume_num), str(issue_num))
        self._logger.info(f"Processing Issue URL: {issue_url}")

        try:
            scraper = self._scrape_url(issue_url)

            # find all the URLs to the articles where I can grab the PDF links (one per article URL, if lambda returns
            # True, it will be included in the list)
            tags = scraper.find_all("a", class_="at-articleLink", href=lambda href: href and "/article/" in href)

            pdf_links = [
                pdf_link
                for pdf_link in
                map(lambda tag: self._scrape_article(get_scraped_url(tag, self.base_url)), tags)
                if pdf_link
            ]

            self._logger.info(f"PDF links found: {len(pdf_links)}")
            return pdf_links
        except Exception as e:
            self._logger.error(f"Failed to process Issue {issue_num} in Volume {volume_num}. Error: {e}")
            return None

    def _scrape_article(self, article_url: str) -> str | None:
        """
        Scrape a single article.

        Args:
            article_url (str): The article links to scrape.

        Returns:
            str | None: The string containing the PDF link.
        """
        self._logger.info(f"Processing Article URL: {article_url}")

        try:
            scraper = self._scrape_url(article_url)

            # Find all PDF links using appropriate class or tag (if lambda returns True, it will be included in the list)
            pdf_tag = scraper.find("a", href=lambda href: href and ".pdf" in href, class_="al-link pdf article-pdfLink")
            if pdf_tag:
                return get_scraped_url(pdf_tag, self.base_url)

            return None
        except Exception as e:
            self._logger.error(f"Failed to process Article {article_url}. Error: {e}")
            return None
