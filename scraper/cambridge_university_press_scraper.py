from typing import List, Type
from bs4 import Tag, ResultSet

from model.cambridge_university_press_models import CambridgeUniversityPressConfig
from scraper.base_pagination_publisher_scraper import BasePaginationPublisherScraper
from utils import get_scraped_url


class CambridgeUniversityPressScraper(BasePaginationPublisherScraper):
    @property
    def config_model_type(self) -> Type[CambridgeUniversityPressConfig]:
        """
        Return the configuration model type.

        Returns:
            Type[CambridgeUniversityPressConfig]: The configuration model type
        """
        return CambridgeUniversityPressConfig

    def scrape(self, model: CambridgeUniversityPressConfig) -> List[Tag] | None:
        """
        Scrape the Cambridge University Press sources for PDF links.

        Args:
            model (CambridgeUniversityPressConfig): The configuration model.

        Returns:
            List[Tag] | None: A list of Tag objects containing the tags to the PDF links. If no tag was found, return None.
        """
        pdf_tags = [
            pdf_tag
            for idx, source in enumerate(model.sources)
            for tag in self._scrape_landing_page(source.landing_page_url, idx + 1)
            for pdf_tag in self._scrape_pagination(
                f"{get_scraped_url(tag, self.base_url)}?pageNum={{page_number}}",
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
            scraper = self._scrape_url_by_bs4(landing_page_url)

            # Find all PDF links using appropriate class or tag (if lambda returns True, it will be included in the list)
            return scraper.find_all("a", href=lambda href: href and "/core/" in href and "/issue/" in href, class_="row")
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
            scraper = self._scrape_url_by_bs4(url)

            # Find all PDF links using appropriate class or tag (if lambda returns True, it will be included in the list)
            pdf_tag_list = scraper.find_all("a", href=lambda href: href and ".pdf" in href)

            self._logger.info(f"PDF links found: {len(pdf_tag_list)}")
            return pdf_tag_list
        except Exception as e:
            self._logger.error(f"Failed to process URL {url}. Error: {e}")
            return None
