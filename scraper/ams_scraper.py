import os
from typing import Type
from selenium.webdriver.common.by import By

from helper.utils import get_scraped_url, get_link_for_accessible_article
from model.ams_models import AMSConfig, AMSJournal
from model.base_iterative_publisher_models import (
    IterativePublisherScrapeJournalOutput,
    IterativePublisherScrapeVolumeOutput,
    IterativePublisherScrapeIssueOutput,
)
from scraper.base_iterative_publisher_scraper import BaseIterativePublisherScraper


class AMSScraper(BaseIterativePublisherScraper):
    @property
    def config_model_type(self) -> Type[AMSConfig]:
        """
        Return the configuration model type.

        Returns:
            Type[AMSConfig]: The configuration model type
        """
        return AMSConfig

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
            res = self._scrape_issue(journal, volume_num, issue)
            if res is None:
                break
            if len(res) > 0:
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
            IterativePublisherScrapeIssueOutput | None: A list of PDF links found in the issue, or None if something went wrong.
        """
        issue_url = os.path.join(
            self._config_model.base_url,
            f"view/journals/{journal.code}/{volume_num}/{issue_num}",
            f"{journal.code}.{volume_num}.issue-{issue_num}.xml"
        )
        self._logger.info(f"Processing Issue URL: {issue_url}")

        try:
            scraper = self._scrape_url(issue_url)
            if any(keyword in scraper.text.lower() for keyword in ["not found", "maintenance"]):
                self._logger.warning(f"Issue {issue_num} in Volume {volume_num} not found or under maintenance.")
                return None

            # find all the article links in the issue by keeping only the links to the accessible articles
            article_links = [
                link
                for tag in self._driver.find_elements(
                    value=f"//a[contains(@class, 'c-Button--link') and contains(@href, '/view/journals/{journal.code}/{volume_num}/{issue_num}/')]",
                    by=By.XPATH,
                )
                if (link := get_link_for_accessible_article(
                    tag,
                    self._config_model.base_url,
                    "../../preceding-sibling::div/div[contains(@class, 'ico-access-open') or contains(@class, 'ico-access-free')]"
                ))
            ]
            pdf_links = [pdf_link for link in article_links if (pdf_link := self._scrape_article(link))]

            self._logger.debug(f"PDF links found: {len(pdf_links)}")
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
            scraper = self._scrape_url(article_url)

            pdf_tag = scraper.find("a", href=True, class_="pdf-download")
            if pdf_tag:
                return get_scraped_url(pdf_tag, self._config_model.base_url)

            return None
        except Exception as e:
            self._logger.error(f"Failed to process Article {article_url}. Error: {e}")
            return None