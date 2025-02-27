from abc import abstractmethod
from typing import List
from bs4 import ResultSet, Tag

from model.base_pagination_publisher_models import BasePaginationPublisherScrapeOutput
from scraper.base_scraper import BaseScraper


class BasePaginationPublisherScraper(BaseScraper):
    def _scrape_pagination(
        self, base_url: str, source_number: int, base_zero: bool = False, **kwargs
    ) -> List[Tag]:
        """
        Scrape the pagination URL for PDF links.

        Args:
            base_url (str): The base URL to scrape.
            source_number (int): The source number.
            base_zero (bool): If the page number is base zero. Default is False.

        Returns:
            List[Tag]: A list of Tag objects containing the tags to the PDF links.
        """
        page_number = 0 if base_zero else 1
        page_size = kwargs.get("page_size", 50)
        max_allowed_papers = kwargs.get("max_allowed_papers")

        pdf_tag_list = []
        while True:
            start_index = (page_number if base_zero else page_number - 1) * page_size
            if max_allowed_papers is not None and start_index >= max_allowed_papers:
                break

            # parse the query with parameters
            # they are enclosed in curly braces, must be replaced with the actual values
            # "page_number", "source_number" and "start_index" are reserved keywords
            page_url = base_url.format(**(
                kwargs | {"page_number": page_number, "source_number": source_number, "start_index": start_index}
            ))

            self._logger.info(f"Processing Page {page_url}")

            page_tag_list = self._scrape_page(page_url)
            if not self._is_valid_tag_list(page_tag_list):
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
        return list(set([link for links in scrape_output.values() for link in links]))

    def _is_valid_tag_list(self, page_tag_list: List | None) -> bool:
        return page_tag_list is not None and len(page_tag_list) > 0

    @abstractmethod
    def scrape(self) -> BasePaginationPublisherScrapeOutput | None:
        """
        Scrape the resources links. This method must be implemented in the derived class.

        Returns:
            BasePaginationPublisherScrapeOutput | None: The output of the scraping, i.e., a dictionary containing the PDF links. Each key is the name of the source which PDF links have been found for, and the value is the list of PDF links itself.
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
