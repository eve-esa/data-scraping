import os
from typing import Type

from helper.utils import get_scraped_url_by_bs_tag, get_scraped_url_by_web_element, get_ancestor
from model.base_iterative_publisher_models import IterativePublisherScrapeIssueOutput
from model.oxford_academic_models import OxfordAcademicConfig, OxfordAcademicJournal
from scraper.base_iterative_publisher_scraper import BaseIterativePublisherScraper


class OxfordAcademicScraper(BaseIterativePublisherScraper):
    @property
    def config_model_type(self) -> Type[OxfordAcademicConfig]:
        """
        Return the configuration model type.

        Returns:
            Type[OxfordAcademicConfig]: The configuration model type
        """
        return OxfordAcademicConfig

    def journal_identifier(self, model: OxfordAcademicJournal) -> str:
        """
        Return the journal identifier.

        Args:
            model (OxfordAcademicJournal): The configuration model.

        Returns:
            str: The journal identifier
        """
        return model.code

    def _scrape_issue(
        self, journal: OxfordAcademicJournal, volume_num: int, issue_num: int
    ) -> IterativePublisherScrapeIssueOutput | None:
        """
        Scrape the issue URL for PDF links.

        Args:
            journal (OxfordAcademicJournal): The journal to scrape.
            volume_num (int): The volume number.
            issue_num (int): The issue number.

        Returns:
            IterativePublisherScrapeIssueOutput | None: A list of PDF links found in the issue, or None is something went wrong.
        """
        issue_url = os.path.join(self._config_model.base_url, journal.code, "issue", str(volume_num), str(issue_num))
        self._logger.info(f"Processing Issue URL: {issue_url}")

        try:
            self._scrape_url(issue_url)

            try:
                tags = self._driver.cdp.find_all("i.icon-availability_open")
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
                return get_scraped_url_by_bs_tag(pdf_tag, self._config_model.base_url)

            self._save_failure(article_url)
            return None
        except Exception as e:
            self._log_and_save_failure(article_url, f"Failed to process Article {article_url}. Error: {e}")
            return None
