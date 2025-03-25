import os
from typing import Type, List
from urllib.parse import urlparse

from helper.utils import get_scraped_url_by_bs_tag, get_scraped_url_by_web_element, get_ancestor
from model.base_iterative_publisher_models import IterativePublisherScrapeIssueOutput
from model.oxford_academic_models import OxfordAcademicConfig, OxfordAcademicJournal
from model.sql_models import ScraperFailure
from scraper.base_iterative_publisher_scraper import BaseIterativePublisherScraper


class OxfordAcademicScraper(BaseIterativePublisherScraper):
    @property
    def config_model_type(self) -> Type[OxfordAcademicConfig]:
        return OxfordAcademicConfig

    def journal_identifier(self, model: OxfordAcademicJournal) -> str:
        return model.code

    def _scrape_issue(
        self, journal: OxfordAcademicJournal, volume_num: int, issue_num: int
    ) -> IterativePublisherScrapeIssueOutput | None:
        issue_url = os.path.join(journal.url, "issue", str(volume_num), str(issue_num))
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

        path = parsed_url.path.lstrip("/")
        _, _, volume_num, issue_num = path.split("/")

        try:
            self._scrape_url(issue_url)

            try:
                tags = self._driver.cdp.find_all("i.icon-availability_open", timeout=0.5)
            except:
                tags = []

            # find all the URLs to the articles where I can grab the PDF links
            articles_links = [
                get_scraped_url_by_web_element(a_tag, self._config_model.base_url)
                for tag in tags
                if (ancestor := get_ancestor(tag, "h5.customLink.item-title"))
                   and (a_tag := ancestor.query_selector("a.at-articleLink"))
                   and (href := a_tag.get_attribute("href"))
                   and "/article/" in href
            ]

            pdf_links = [
                pdf_link for pdf_link in map(lambda link: self._scrape_article(link), articles_links) if pdf_link
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
        try:
            scraper = self._scrape_url(article_url)

            # Find all PDF links using appropriate class or tag (if lambda returns True, it will be included in the list)
            pdf_tag = scraper.find("a", href=lambda href: href and ".pdf" in href, class_="al-link pdf article-pdfLink")
            if pdf_tag:
                return get_scraped_url_by_bs_tag(pdf_tag, self._config_model.base_url)

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
