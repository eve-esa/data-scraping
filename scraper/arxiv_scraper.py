from typing import Type, List
from bs4 import ResultSet, Tag

from model.arxiv_models import ArxivConfig
from scraper.base_pagination_publisher_scraper import BasePaginationPublisherScraper


class ArxivScraper(BasePaginationPublisherScraper):
    def __init__(self):
        super().__init__()
        self.__page_size = None

    @property
    def config_model_type(self) -> Type[ArxivConfig]:
        """
        Return the configuration model type.

        Returns:
            Type[ArxivConfig]: The configuration model type
        """
        return ArxivConfig

    def scrape(self, model: ArxivConfig) -> List[Tag] | None:
        """
        Scrape the Sage sources for PDF links.

        Args:
            model (ArxivConfig): The configuration model.

        Returns:
            List[Tag] | None: A list of Tag objects containing the tags to the PDF links. If no tag was found, return None.
        """
        pdf_tags = []
        for idx, source in enumerate(model.sources):
            self.__page_size = source.page_size
            pdf_tags.extend(self._scrape_landing_page(source.landing_page_url, idx + 1))

        return pdf_tags if pdf_tags else None

    def _scrape_landing_page(self, landing_page_url: str, source_number: int) -> List[Tag]:
        """
        Scrape the landing page. If the source has a landing page, scrape the landing page for PDF links. If the source
        has a landing page and the `should_store` is True, store the PDF tags from the landing page. Otherwise, return
        an empty list.

        Args:
            landing_page_url (str): The landing page to scrape.

        Returns:
            List[Tag]: A list of Tag objects containing the tags to the PDF links. If something went wrong, an empty list.
        """
        self._logger.info(f"Processing Landing Page {landing_page_url}")

        return self._scrape_pagination(landing_page_url, source_number, base_zero=True, page_size=self.__page_size)

    def _scrape_page(self, url: str) -> ResultSet | None:
        """
        Scrape the PubMed page of the collection from pagination for PDF links.

        Args:
            url (str): The URL to scrape.

        Returns:
            ResultSet | None: A ResultSet (i.e., a list) containing the tags to the PDF links. If something went wrong, return None.
        """
        try:
            scraper = self._scrape_url_by_bs4(url)

            # Now, visit each article link and find the PDF link
            pdf_tag_list = scraper.find_all("a", href=lambda href: href and "/pdf/" in href)

            self._logger.info(f"PDF links found: {len(pdf_tag_list)}")
            return pdf_tag_list
        except Exception as e:
            self._logger.error(f"Failed to process URL {url}. Error: {e}")
            return None
