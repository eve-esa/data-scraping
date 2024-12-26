from typing import Type, List
from bs4 import ResultSet, Tag

from scraper.base_pagination_publisher_scraper import BasePaginationPublisherScraper, BasePaginationPublisherSource
from scraper.base_scraper import BaseConfigScraper


class NCBISource(BasePaginationPublisherSource):
    pagination_url: str


class NCBIConfig(BaseConfigScraper):
    sources: List[NCBISource]


class NCBIScraper(BasePaginationPublisherScraper):
    @property
    def config_model_type(self) -> Type[NCBIConfig]:
        """
        Return the configuration model type.

        Returns:
            Type[NCBIConfig]: The configuration model type
        """
        return NCBIConfig

    @property
    def cookie_selector(self) -> str:
        return ""

    @property
    def base_url(self) -> str:
        return "https://www.ncbi.nlm.nih.gov"

    def scrape(self, model: NCBIConfig) -> List[Tag] | None:
        """
        Scrape the source URLs of for PDF links.

        Args:
            model (NCBIConfig): The configuration model.

        Returns:
            List[Tag] | None: A list of Tag objects containing the tags to the PDF links. If no tag was found, return None.
        """
        pdf_tags = []
        for idx, source in enumerate(model.sources):
            self._scrape_landing_page(source.landing_page_url, idx + 1)
            pdf_tags.extend(self._scrape_pagination(source.pagination_url, idx + 1))

        return pdf_tags if pdf_tags else None

    def _scrape_landing_page(self, landing_page_url: str, source_number: int) -> None:
        """
        Scrape the landing page. If the source has a landing page, scrape the landing page for PDF links. If the source
        has a landing page and the `should_store` is True, store the PDF tags from the landing page. Otherwise, return
        an empty list.

        Args:
            landing_page_url (str): The landing page to scrape.

        Returns:
            List[Tag]: A list of Tag objects containing the tags to the PDF links, if the source has a landing page and the `should_store` is True. Otherwise, an empty list.
        """
        self._logger.info(f"Processing Landing Page {landing_page_url}")

        self._scrape_page(landing_page_url, 0, source_number, False)

    def _scrape_page(self, url: str, page_number: int, source_number: int, show_logs: bool = True) -> ResultSet | None:
        """
        Scrape the PubMed page of the collection from pagination for PDF links.

        Args:
            url (str): The URL to scrape.
            page_number (int): The page number.
            source_number (int): The source number.
            show_logs (bool): Whether to show logs.

        Returns:
            ResultSet: A ResultSet (i.e., a list) or a list of Tag objects containing the tags to the PDF links, or None if something went wrong.
        """
        try:
            scraper = self._scrape_url(url)

            # Find all PDF links using appropriate class or tag (if lambda returns True, it will be included in the list)
            pdf_tag_list = scraper.find_all("a", href=lambda href: href and "/articles/" in href and ".pdf" in href, class_="view")

            if show_logs:
                self._logger.info(f"PDF links found: {len(pdf_tag_list)}")
            return pdf_tag_list
        except Exception as e:
            self._logger.error(f"Failed to process URL {url}. Error: {e}")
            return None