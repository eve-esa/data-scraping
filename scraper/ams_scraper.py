import os
from typing import Type

from model.ams_models import AMSConfig, AMSJournal
from model.base_iterative_publisher_models import (
    IterativePublisherScrapeJournalOutput,
    IterativePublisherScrapeVolumeOutput,
    IterativePublisherScrapeIssueOutput,
)
from scraper.base_iterative_publisher_scraper import BaseIterativePublisherScraper
from utils import get_scraped_url


class AMSScraper(BaseIterativePublisherScraper):
    @property
    def config_model_type(self) -> Type[AMSConfig]:
        """
        Return the configuration model type.

        Returns:
            Type[AMSConfig]: The configuration model type
        """
        return AMSConfig

    @property
    def cookie_selector(self) -> str:
        return ""

    @property
    def base_url(self) -> str:
        return "https://journals.ametsoc.org"

    @property
    def file_extension(self) -> str:
        """
        Return the file extension of the source files.

        Returns:
            str: The file extension of the source files
        """
        return ".pdf"

    def journal_identifier(self, model: AMSJournal) -> str:
        """
        Return the journal identifier.

        Args:
            model (AMSJournal): The configuration model.

        Returns:
            str: The journal identifier
        """
        return model.code

    def _scrape_journal(self, journal: AMSJournal) -> IterativePublisherScrapeJournalOutput:
        """
        Scrape all volumes of a journal.

        Args:
            journal (AMSJournal): The journal to scrape.

        Returns:
            IterativePublisherScrapeJournalOutput: A dictionary containing the PDF links.
        """
        self._logger.info(f"Processing Journal {journal.name}")

        volume = 1

        links = {}
        while True:
            if not (res := self._scrape_volume(journal, volume)):
                break

            links[volume] = res
            volume += 1  # Move to next volume

        return links

    def _scrape_volume(self, journal: AMSJournal, volume_num: int) -> IterativePublisherScrapeVolumeOutput:
        """
        Scrape all issues of a volume.

        Args:
            journal (AMSJournal): The journal to scrape.
            volume_num (int): The volume number.

        Returns:
            IterativePublisherScrapeVolumeOutput: A dictionary containing the PDF links.
        """
        self._logger.info(f"Processing Volume {volume_num}")

        issue = 1
        links = {}
        while True:
            if not (res := self._scrape_issue(journal, volume_num, issue)):
                break

            links[issue] = res
            issue += 1  # Move to next issue

        return links

    def _scrape_issue(
        self, journal: AMSJournal, volume_num: int, issue_num: int
    ) -> IterativePublisherScrapeIssueOutput | None:
        """
        Scrape the issue URL for PDF links.

        Args:
            journal (AMSJournal): The journal to scrape.
            volume_num (int): The volume number.
            issue_num (int): The issue number.

        Returns:
            IterativePublisherScrapeIssueOutput | None: A list of PDF links found in the issue, or None is something went wrong.
        """
        issue_url = os.path.join(self.base_url, "view/journals", journal.code, str(volume_num), str(issue_num), f"{journal.code}.{volume_num}.issue-{issue_num}.xml")
        self._logger.info(f"Processing Issue URL: {issue_url}")

        try:
            scraper = self._scrape_url_by_bs4(issue_url)

            # find all the URLs to the articles where I can grab the PDF links (one per article URL, if lambda returns
            # True, it will be included in the list)
            tags = scraper.find_all(
                "a",
                class_="c-Button--link",
                href=lambda href: href and f"/view/journals/{journal.code}/{volume_num}/{issue_num}/" in href
            )

            pdf_links = [
                pdf_link
                for pdf_link in map(lambda tag: self._scrape_article(get_scraped_url(tag, self.base_url)), tags)
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
            str | None: The string containing the PDF link, or None if no link was found or something went wrong.
        """
        self._logger.info(f"Processing Article URL: {article_url}")

        try:
            scraper = self._scrape_url_by_bs4(article_url)

            pdf_tag = scraper.find("a", href=True, class_="pdf-download")  # Update 'pdf-download' as needed
            if pdf_tag:
                return get_scraped_url(pdf_tag, self.base_url)

            return None
        except Exception as e:
            self._logger.error(f"Failed to process Article {article_url}. Error: {e}")
            return None