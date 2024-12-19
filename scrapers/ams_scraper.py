from typing import List, Type
from bs4 import Tag
from pydantic import BaseModel

from scrapers.base_scraper import BaseConfigScraper
from scrapers.iterative_publisher_scraper import (
    IterativePublisherScraper,
    IterativePublisherScrapeJournalOutput,
    IterativePublisherScrapeVolumeOutput,
    IterativePublisherScrapeIssueOutput,
    IterativePublisherScrapeOutput,
)
from utils import get_scraped_urls


class AMSJournal(BaseModel):
    name: str
    code: str


class AMSConfig(BaseConfigScraper):
    journals: List[AMSJournal]


class AMSScraper(IterativePublisherScraper):
    @property
    def model_class(self) -> Type[AMSConfig]:
        """
        Return the configuration model class.

        Returns:
            Type[AMSConfig]: The configuration model class.
        """
        return AMSConfig

    @property
    def cookie_selector(self) -> str:
        return ""

    def scrape(self, model: AMSConfig) -> IterativePublisherScrapeOutput:
        """
        Scrape the AMS journals for PDF links.

        Args:
            model (AMSConfig): The configuration model.

        Returns:
            IterativePublisherScrapeOutput: A dictionary containing the PDF links.
        """
        links = {}

        for journal in model.journals:
            links[journal.code] = self._scrape_journal(journal)

        return links

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

        result = {}
        while True:
            res = self._scrape_volume(journal.code, volume)
            if not res:
                break

            result[volume] = res
            volume += 1  # Move to next volume

        return result

    def _scrape_volume(self, journal_code: str, volume_num: int) -> IterativePublisherScrapeVolumeOutput:
        """
        Scrape all issues of a volume.

        Args:
            journal_code (str): The journal code.
            volume_num (int): The volume number.

        Returns:
            IterativePublisherScrapeVolumeOutput: A dictionary containing the PDF links.
        """
        self._logger.info(f"Processing Volume {volume_num}")

        issue = 1
        result = {}
        while True:
            res = self._scrape_issue(journal_code, volume_num, issue)
            if res is None:
                break

            result[issue] = res
            issue += 1  # Move to next issue

        return result

    def _scrape_issue(self, journal_code: str, volume_num: int, issue_num: int) -> IterativePublisherScrapeIssueOutput:
        """
        Scrape the issue URL for PDF links.

        Args:
            journal_code (str): The journal code.
            volume_num (int): The volume number.
            issue_num (int): The issue number.

        Returns:
            IterativePublisherScrapeIssueOutput: A list of PDF links found in the issue.
        """
        base_url = "https://journals.ametsoc.org"
        issue_url = f"{base_url}/view/journals/{journal_code}/{volume_num}/{issue_num}/{journal_code}.{volume_num}.issue-{issue_num}.xml"
        self._logger.info(f"Processing Issue URL: {issue_url}")

        scraper = self._scrape_url(issue_url)
        try:
            # find all the URLs to the articles where I can grab the PDF links (one per article URL, if lambda returns
            # True, it will be included in the list)
            article_urls = get_scraped_urls(
                scraper,
                base_url,
                href=lambda href: href and f"/view/journals/{journal_code}/{volume_num}/{issue_num}/" in href,
                class_="c-Button--link",
            )

            pdf_links = [
                base_url + tag.get("href")
                if tag.get("href").startswith("/") else tag.get("href")
                for tag in self._scrape_article(article_urls, base_url)
            ]

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

    def _scrape_article(self, article_urls: List[str], base_url: str) -> List[Tag]:
        """
        Scrape a single article.

        Args:
            article_urls (List[str]): The article links to scrape.
            base_url (str): The base URL.

        Returns:
            List[Tag]: A list of Tag objects containing the PDF links.
        """
        pdf_links = []
        for article_url in article_urls:
            self._logger.info(f"Processing Article URL: {article_url}")

            scraper = self._scrape_url(article_url)

            pdf_link = scraper.find("a", href=True, class_="pdf-download")  # Update 'pdf-download' as needed
            if pdf_link:
                pdf_links.append(pdf_link)

        return pdf_links