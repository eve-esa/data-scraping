import os
from typing import List, Type

from scraper.base_iterative_publisher_scraper import (
    BaseIterativePublisherScraper,
    IterativePublisherScrapeJournalOutput,
    IterativePublisherScrapeVolumeOutput,
    IterativePublisherScrapeIssueOutput,
    BaseIterativePublisherConfig,
    BaseIterativePublisherJournal,
)
from utils import get_scraped_url


class OxfordAcademicJournal(BaseIterativePublisherJournal):
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

    @property
    def file_extension(self) -> str:
        """
        Return the file extension of the source files.

        Returns:
            str: The file extension of the source files
        """
        return ".pdf"

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
            journal (OxfordAcademicJournal): The journal to scrape.

        Returns:
            IterativePublisherScrapeJournalOutput: A dictionary containing the PDF links.
        """
        self._logger.info(f"Processing Journal {journal.name}")
        return self._build_journal_links(journal)

    def _scrape_volume(self, journal: OxfordAcademicJournal, volume_num: int) -> IterativePublisherScrapeVolumeOutput:
        """
        Scrape all issues of a volume.

        Args:
            journal (OxfordAcademicJournal): The journal to scrape.
            volume_num (int): The volume number.

        Returns:
            IterativePublisherScrapeVolumeOutput: A dictionary containing the PDF links.
        """
        self._logger.info(f"Processing Volume {volume_num}")
        return self._build_volume_links(journal, volume_num)

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
        issue_url = os.path.join(self.base_url, journal.code, "issue", str(volume_num), str(issue_num))
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
