import os
from typing import Type, Dict, List
from bs4 import ResultSet, Tag

from helper.utils import get_scraped_url
from model.base_iterative_publisher_models import (
    IterativePublisherScrapeJournalOutput,
    IterativePublisherScrapeVolumeOutput,
    IterativePublisherScrapeIssueOutput,
)
from model.base_mapped_models import BaseMappedPaginationConfig
from model.base_pagination_publisher_models import BasePaginationPublisherScrapeOutput
from model.mdpi_models import MDPIConfig, MDPIJournal
from scraper.base_iterative_publisher_scraper import BaseIterativePublisherScraper
from scraper.base_mapped_publisher_scraper import BaseMappedPublisherScraper
from scraper.base_pagination_publisher_scraper import BasePaginationPublisherScraper
from scraper.base_scraper import BaseMappedScraper


class MDPIScraper(BaseMappedPublisherScraper):
    @property
    def mapping(self) -> Dict[str, Type[BaseMappedScraper]]:
        return {
            "MDPIJournalsScraper": MDPIJournalsScraper,
            "MDPIGoogleSearchScraper": MDPIGoogleSearchScraper,
        }


class MDPIJournalsScraper(BaseIterativePublisherScraper, BaseMappedScraper):
    @property
    def config_model_type(self) -> Type[MDPIConfig]:
        """
        Return the configuration model type.

        Returns:
            Type[MDPIConfig]: The configuration model type
        """
        return MDPIConfig

    def journal_identifier(self, model: MDPIJournal) -> str:
        """
        Return the journal identifier.

        Args:
            model (MDPIJournal): The configuration model.

        Returns:
            str: The journal identifier
        """
        return model.name

    def _scrape_journal(self, journal: MDPIJournal) -> IterativePublisherScrapeJournalOutput:
        """
        Scrape all volumes of a journal.

        Args:
            journal (MDPIJournal): The journal to scrape.

        Returns:
            IterativePublisherScrapeJournalOutput: A dictionary containing the PDF links.
        """
        self._logger.info(f"Processing Journal {journal.name}")
        return self._build_journal_links(journal)

    def _scrape_volume(self, journal: MDPIJournal, volume_num: int) -> IterativePublisherScrapeVolumeOutput:
        """
        Scrape all issues of a volume.

        Args:
            journal (MDPIJournal): The journal to scrape.
            volume_num (int): The volume number.

        Returns:
            IterativePublisherScrapeVolumeOutput: A dictionary containing the PDF links.
        """
        self._logger.info(f"Processing Volume {volume_num}")
        return self._build_volume_links(journal, volume_num)

    def _scrape_issue(
        self, journal: MDPIJournal, volume_num: int, issue_num: int
    ) -> IterativePublisherScrapeIssueOutput | None:
        """
        Scrape the issue URL for PDF links.

        Args:
            journal (MDPIJournal): The journal to scrape.
            volume_num (int): The volume number.
            issue_num (int): The issue number.

        Returns:
            IterativePublisherScrapeIssueOutput | None: A list of PDF links found in the issue, or None is something went wrong.
        """
        issue_url = os.path.join(journal.url, str(volume_num), str(issue_num))
        self._logger.info(f"Processing Issue URL: {issue_url}")

        try:
            scraper = self._scrape_url(issue_url)

            # Get all PDF links using Selenium to scroll and handle cookie popup once
            # Now find all PDF links using the class_="UD_Listings_ArticlePDF"
            tags = scraper.find_all("a", class_="UD_Listings_ArticlePDF", href=True)
            pdf_links = [get_scraped_url(tag, self.base_url) for tag in tags]

            self._logger.debug(f"PDF links found: {len(pdf_links)}")
            return pdf_links
        except Exception as e:
            self._logger.error(
                f"Failed to process Issue {issue_num} in Volume {volume_num}. Error: {e}"
            )
            return None

    def _scrape_article(self, *args, **kwargs) -> str | None:
        """
        Scrape a single article.

        Returns:
            str | None: The string containing the PDF link.
        """
        pass


class MDPIGoogleSearchScraper(BasePaginationPublisherScraper, BaseMappedScraper):
    def __init__(self):
        super().__init__()
        self.__page_size = None
        self.__cookie_selector = None
        self.__forbidden_keywords = ("accounts.google.com", "site:", "translate.google.com")

    @property
    def config_model_type(self) -> Type[BaseMappedPaginationConfig]:
        return BaseMappedPaginationConfig

    def scrape(self, model: BaseMappedPaginationConfig) -> BasePaginationPublisherScrapeOutput | None:
        pdf_tags = []
        self.__cookie_selector = self._config_model.cookie_selector
        self._config_model.cookie_selector = None
        for idx, source in enumerate(model.sources):
            self.__page_size = source.page_size
            pdf_tags.extend(self._scrape_landing_page(source.landing_page_url, idx + 1))

        return {"MDPI Google Search": [get_scraped_url(tag, self.base_url) for tag in pdf_tags]} if pdf_tags else None

    def _scrape_landing_page(self, landing_page_url: str, source_number: int) -> ResultSet | List[Tag] | None:
        self._logger.info(f"Processing Landing Page {landing_page_url}")

        return self._scrape_pagination(landing_page_url, source_number, base_zero=True, page_size=self.__page_size)

    def _scrape_page(self, url: str) -> ResultSet | List[Tag] | None:
        def get_mdpi_pdf_tags(mdpi_tag: Tag):
            mdpi_url = mdpi_tag.get("href")
            tags = self._scrape_url(mdpi_url).find_all(
                "a",
                href=True,
                class_=lambda class_: class_ and ("UD_Listings_ArticlePDF" in class_ or "UD_ArticlePDF" in class_),
            )
            self._logger.debug(f"MDPI URL {mdpi_url} processed; PDF links found: {len(tags)}")
            return tags

        try:
            # first of all, scrape the Google Search URL
            scraper = self._scrape_url(url)
            mdpi_tags = scraper.find_all(
                "a",
                href=lambda href: href and "www.mdpi.com" in href and not any(
                    x in href for x in self.__forbidden_keywords
                ),
            )

            self._config_model.cookie_selector = self.__cookie_selector
            pdf_tag_list = [tag for mdpi_tag in mdpi_tags for tag in get_mdpi_pdf_tags(mdpi_tag)]

            self._logger.debug(f"PDF links found: {len(pdf_tag_list)}")
            return pdf_tag_list
        except Exception as e:
            self._logger.error(f"Failed to process URL {url}. Error: {e}")
            return None
