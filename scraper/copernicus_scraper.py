import os
from typing import Type, List
from urllib.parse import urlparse

from helper.utils import get_scraped_url_by_bs_tag
from model.base_iterative_publisher_models import (
    IterativePublisherScrapeIssueOutput,
    BaseIterativeWithConstraintPublisherConfig,
    BaseIterativeWithConstraintPublisherJournal,
)
from model.sql_models import ScraperFailure
from scraper.base_iterative_publisher_scraper import BaseIterativeWithConstraintPublisherScraper


class CopernicusScraper(BaseIterativeWithConstraintPublisherScraper):
    @property
    def config_model_type(self) -> Type[BaseIterativeWithConstraintPublisherConfig]:
        return BaseIterativeWithConstraintPublisherConfig

    def journal_identifier(self, model: BaseIterativeWithConstraintPublisherJournal) -> str:
        return model.name

    def _scrape_issue(
        self, journal: BaseIterativeWithConstraintPublisherJournal, volume_num: int, issue_num: int
    ) -> IterativePublisherScrapeIssueOutput | None:
        issue_url = os.path.join(journal.url, "articles", str(volume_num), f"issue{issue_num}.html")
        self._logger.info(f"Processing Issue URL: {issue_url}")
        return self.__scrape_issue(issue_url)

    def __scrape_issue(self, issue_url: str) -> IterativePublisherScrapeIssueOutput | None:
        """
        Scrape the issue URL for PDF links.

        Args:
            issue_url (str): The issue URL to scrape.

        Returns:
            IterativePublisherScrapeIssueOutput | None: A list of PDF links found in the issue, or None is something went wrong
        """
        parsed_url = urlparse(issue_url)
        journal_url = f"{parsed_url.scheme}://{parsed_url.netloc}"

        path = parsed_url.path.lstrip("/")
        _, volume_num, issue_num = path.split("/")
        issue_num = issue_num.replace("issue", "").replace(".html", "")

        try:
            scraper = self._scrape_url(issue_url)

            # find all the URLs to the articles where I can grab the PDF links (one per article URL, if lambda returns
            # True, it will be included in the list)
            tags = scraper.find_all("a", class_="article-title", href=lambda href: href and "/articles/" in href)

            pdf_links = [
                pdf_link
                for pdf_link in map(
                    lambda tag: self._scrape_article(get_scraped_url_by_bs_tag(tag, journal_url)), tags
                )
                if pdf_link
            ]

            self._logger.debug(f"PDF links found: {len(pdf_links)}")
            return pdf_links
        except Exception as e:
            self._log_and_save_failure(issue_url, f"Failed to process Issue {issue_num} in Volume {volume_num}. Error: {e}")
            return None

    def _scrape_article(self, article_url: str) -> str | None:
        self._logger.info(f"Processing Article URL: {article_url}")
        return self.__scrape_article(article_url)

    def __scrape_article(self, article_url: str) -> str | None:
        """
        Scrape a single article.

        Args:
            article_url (str): The article URL to scrape.

        Returns:
            str | None: The string containing the PDF link.
        """
        parsed_url = urlparse(article_url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"

        try:
            scraper = self._scrape_url(article_url)

            # Find all PDF links using appropriate class or tag (if lambda returns True, it will be included in the list)
            if pdf_tag := scraper.find("a", href=lambda href: href and ".pdf" in href):
                return get_scraped_url_by_bs_tag(pdf_tag, base_url)

            self._save_failure(article_url)
            return None
        except Exception as e:
            self._log_and_save_failure(article_url, f"Failed to process Article {article_url}. Error: {e}")
            return None

    def scrape_failure(self, failure: ScraperFailure) -> List[str]:
        link = failure.source
        self._logger.info(f"Scraping URL: {link}")

        message = failure.message.lower()
        res = self.__scrape_issue(link) if "issue" in message else self.__scrape_article(link)

        return [res] if res else []
