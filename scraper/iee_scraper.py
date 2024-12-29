from typing import List, Type
from bs4 import Tag, ResultSet

from scraper.base_pagination_publisher_scraper import BasePaginationPublisherSource, BasePaginationPublisherScraper
from scraper.base_scraper import BaseConfigScraper
from utils import get_scraped_url


class IEEEConfig(BaseConfigScraper):
    sources: List[BasePaginationPublisherSource]


class IEEEScraper(BasePaginationPublisherScraper):
    @property
    def config_model_type(self) -> Type[IEEEConfig]:
        """
        Return the configuration model type.

        Returns:
            Type[IEEEConfig]: The configuration model type
        """
        return IEEEConfig

    @property
    def cookie_selector(self) -> str:
        return "button.osano-cm-accept-all"

    @property
    def base_url(self) -> str:
        return "https://ieeexplore.ieee.org"

    @property
    def file_extension(self) -> str:
        """
        Return the file extension of the source files.

        Returns:
            str: The file extension of the source files
        """
        return ".pdf"

    def scrape(self, model: IEEEConfig) -> List[Tag] | None:
        """
        Scrape the IEEE sources for PDF links.

        Args:
            model (IEEEConfig): The configuration model.

        Returns:
            List[Tag] | None: A list of Tag objects containing the tags to the PDF links. If no tag was found, return None.
        """
        pdf_tags = [
            pdf_tag
            for idx, source in enumerate(model.sources)
            for tag in self._scrape_landing_page(source.landing_page_url, idx + 1)
            for pdf_tag in self._scrape_pagination(
                f"{get_scraped_url(tag, self.base_url)}&sortType=vol-only-seq&rowsPerPage=100&pageNumber={{page_number}}",
                idx + 1
            )
        ]

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

        try:
            scraper = self._scrape_url(landing_page_url)

            # Find all PDF links using appropriate class or tag (if lambda returns True, it will be included in the list)
            return scraper.find_all("a", href=lambda href: href and "/tocresult" in href and "punumber=" in href)
        except Exception as e:
            self._logger.error(f"Failed to process URL {landing_page_url}. Error: {e}")
            return []

    def _scrape_page(self, url: str) -> ResultSet | None:
        """
        Scrape the PubMed page of the collection from pagination for PDF links.

        Args:
            url (str): The URL to scrape.

        Returns:
            ResultSet | None: A ResultSet (i.e., a list) containing the tags to the PDF links. If something went wrong, return None.
        """
        try:
            scraper = self._scrape_url(url)

            # Find all PDF links using appropriate class or tag (if lambda returns True, it will be included in the list)
            pdf_tag_list = scraper.find_all(
                "a",
                href=lambda href: href and "/stamp/stamp.jsp" in href,
                class_=lambda class_: class_ and "u-flex-display-flex" in class_
            )

            self._logger.info(f"PDF links found: {len(pdf_tag_list)}")
            return pdf_tag_list
        except Exception as e:
            self._logger.error(f"Failed to process URL {url}. Error: {e}")
            return None
