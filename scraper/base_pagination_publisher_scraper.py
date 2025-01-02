from abc import abstractmethod
from typing import List
from bs4 import ResultSet, Tag

from model.base_models import BaseConfigScraper
from model.base_pagination_publisher_models import BasePaginationPublisherScrapeOutput
from scraper.base_scraper import BaseScraper
from utils import get_unique


class BasePaginationPublisherScraper(BaseScraper):
    def _scrape_pagination(self, base_url: str, source_number: int, starting_page_number: int | None = 1) -> List[Tag]:
        """
        Scrape the pagination URL for PDF links.

        Args:
            base_url (str): The base URL to scrape.
            source_number (int): The source number.
            starting_page_number (int | None): The starting page number. Defaults to 1.

        Returns:
            List[Tag]: A list of Tag objects containing the tags to the PDF links.
        """
        page_number = starting_page_number

        pdf_tag_list = []
        while True:
            # parse the query with parameters
            # they are enclosed in curly braces, must be replaced with the actual values
            # "page_number" and "source_number" are reserved keywords
            page_url = base_url.format(**{"page_number": page_number, "source_number": source_number})

            self._logger.info(f"Processing Pagination {page_url}")

            page_tag_list = self._scrape_page(page_url)
            if not page_tag_list:
                break

            pdf_tag_list.extend(page_tag_list)
            page_number += 1

        return pdf_tag_list

    def post_process(self, scrape_output: BasePaginationPublisherScrapeOutput) -> List[str]:
        """
        Extract the href attribute from the links.

        Args:
            scrape_output (BasePaginationPublisherScrapeOutput): A dictionary containing the PDF links. Each key is the name of the source which PDF links have been found for, and the value is the list of PDF links itself.

        Returns:
            List[str]: A list of strings containing the PDF links
        """
        return get_unique([link for links in scrape_output.values() for link in links])

    @abstractmethod
    def scrape(self, model: BaseConfigScraper) -> BasePaginationPublisherScrapeOutput:
        """
        Scrape the resources links. This method must be implemented in the derived class.

        Args:
            model (BaseConfigScraper): The configuration model.

        Returns:
            BasePaginationPublisherScrapeOutput: The output of the scraping, i.e., a dictionary containing the PDF links. Each key is the name of the source which PDF links have been found for, and the value is the list of PDF links itself.
        """
        pass

    @abstractmethod
    def _scrape_landing_page(self, landing_page_url: str, source_number: int) -> ResultSet | List[Tag] | None:
        """
        Scrape the landing page. This method must be implemented in the derived class.

        Args:
            landing_page_url (str): The landing page URL.
            source_number (int): The source number.

        Returns:
            ResultSet | List[Tag] | None: A ResultSet (i.e., a list) or a list of Tag objects containing the tags to the PDF links, or None.
        """
        pass

    @abstractmethod
    def _scrape_page(self, url: str) -> ResultSet | List[Tag] | None:
        """
        Scrape the page. This method must be implemented in the derived class.

        Args:
            url (str): The URL to scrape.

        Returns:
            ResultSet | List[Tag] | None: A ResultSet (i.e., a list) or a list of Tag objects containing the tags to the PDF links. If something went wrong, return None.
        """
        pass
