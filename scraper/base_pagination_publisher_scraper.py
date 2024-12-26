from abc import abstractmethod
from typing import List
from bs4 import ResultSet, Tag
from pydantic import BaseModel

from scraper.base_scraper import BaseScraper
from utils import get_scraped_url


class BasePaginationPublisherSource(BaseModel):
    """
    Configuration model for the base pagination publisher scraper source. The `landing_page_url` is the URL to scrape to
    get the initial pagination URL.

    Variables:
        landing_page_url (str): The landing URL to scrape
    """
    landing_page_url: str


class BasePaginationPublisherScraper(BaseScraper):
    def _scrape_pagination(self, base_url: str, source_number: int) -> ResultSet | List[Tag]:
        """
        Scrape the pagination URL for PDF links.

        Args:
            base_url (str): The base URL to scrape.

        Returns:
            ResultSet | List[Tag]: A ResultSet (i.e., a list) or a list of Tag objects containing the tags to the PDF links.
        """
        page_number = 1

        pdf_tag_list = []
        while True:
            # parse the query with parameters
            # they are enclosed in curly braces, must be replaced with the actual values
            # "page_number" and "source_number" are reserved keywords
            page_url = base_url.format(**{"page_number": page_number, "source_number": source_number})

            self._logger.info(f"Processing Pagination {page_url}")

            page_tag_list = self._scrape_page(page_url, page_number, source_number)
            if not page_tag_list:
                break

            pdf_tag_list.extend(page_tag_list)
            page_number += 1

        return pdf_tag_list

    def post_process(self, scrape_output: ResultSet | List[Tag]) -> List[str]:
        """
        Extract the href attribute from the links.

        Args:
            scrape_output (ResultSet | List[Tag]): A ResultSet (i.e., a list) or a list of Tag objects containing the tags to the PDF links.

        Returns:
            List[str]: A list of strings containing the PDF links
        """
        return [get_scraped_url(tag, self.base_url) for tag in scrape_output]

    @abstractmethod
    def _scrape_landing_page(self, landing_page_url: str, source_number: int) -> List[Tag] | None:
        """
        Scrape the landing page.

        Args:
            landing_page_url (str): The landing page URL.
            source_number (int): The source number.

        Returns:
            List[Tag] | None: A list of Tag objects containing the tags to the PDF links, or None.
        """
        pass

    @abstractmethod
    def _scrape_page(self, url: str, page_number: int, source_number: int, show_logs: bool = True) -> ResultSet | List[Tag] | None:
        """
        Scrape the page.

        Args:
            url (str): The URL to scrape.
            page_number (int): The page number.
            source_number (int): The source number.
            show_logs (bool): Whether to show logs.

        Returns:
            ResultSet | List[Tag] | None: A ResultSet (i.e., a list) or a list of Tag objects containing the tags to the PDF links. If something went wrong, return None.
        """
        pass
