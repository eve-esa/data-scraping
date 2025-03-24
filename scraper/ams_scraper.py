import os
from typing import Type, List

from helper.utils import get_scraped_url_by_web_element
from model.ams_models import AMSConfig, AMSJournal
from model.base_iterative_publisher_models import (
    IterativePublisherScrapeJournalOutput,
    IterativePublisherScrapeVolumeOutput,
    IterativePublisherScrapeIssueOutput,
)
from model.sql_models import ScraperFailure
from scraper.base_iterative_publisher_scraper import BaseIterativePublisherScraper


class AMSScraper(BaseIterativePublisherScraper):
    @property
    def config_model_type(self) -> Type[AMSConfig]:
        return AMSConfig

    def journal_identifier(self, model: AMSJournal) -> str:
        return model.code

    def _scrape_journal(self, journal: AMSJournal) -> IterativePublisherScrapeJournalOutput:
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
        issue_url = os.path.join(
            self._config_model.base_url,
            f"view/journals/{journal.code}/{volume_num}/{issue_num}",
            f"{journal.code}.{volume_num}.issue-{issue_num}.xml"
        )
        self._logger.info(f"Processing Issue URL: {issue_url}")

        return self.__scrape_url(issue_url)

    def _scrape_article(self, article_url: str) -> str | None:
        pass

    def scrape_failure(self, failure: ScraperFailure) -> List[str]:
        link = failure.source
        self._logger.info(f"Scraping URL: {link}")

        return self.__scrape_url(link) or []

    def __scrape_url(self, url: str) -> IterativePublisherScrapeIssueOutput | None:
        xml_page = os.path.split(url)[-1]
        xml_page = xml_page.replace(".xml", "")
        journal_code, volume_num, issue_num = xml_page.split(".")
        issue_num = issue_num.split("-")[-1]

        url_search, _ = os.path.split(url.replace(self._config_model.base_url, ""))

        try:
            self._scrape_url(url)

            # find all the article links in the issue by keeping only the links to the accessible articles
            try:
                tags = self._driver.cdp.find_all("div.ico-access-open", timeout=0.5)
            except:
                tags = []
            try:
                tags += self._driver.cdp.find_all("div.ico-access-free", timeout=0.5)
            except:
                pass

            pdf_links = [
                get_scraped_url_by_web_element(
                    a_tag, self._config_model.base_url
                ).replace("/view/journals/", "/downloadpdf/view/journals/").replace(".xml", ".pdf")
                for tag in tags
                if (grandparent := tag.get_parent().get_parent())
                   and (a_tag := grandparent.query_selector("a.c-Button--link"))
                   and (href := a_tag.get_attribute("href"))
                   and url_search in href
                   and ".xml" in href
            ]

            # Now, visit each article link and find the PDF link
            if not pdf_links:
                self._save_failure(url)
                return None

            self._logger.debug(f"PDF links found: {len(pdf_links)}")
            return pdf_links
        except Exception as e:
            self._log_and_save_failure(url, f"Failed to process Issue {issue_num} in Volume {volume_num}. Error: {e}")
            return None
