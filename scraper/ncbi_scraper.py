from typing import Type
from bs4 import ResultSet

from helper.utils import get_scraped_url
from model.base_pagination_publisher_models import BasePaginationPublisherScrapeOutput
from model.ncbi_models import NCBIConfig
from scraper.base_pagination_publisher_scraper import BasePaginationPublisherScraper


class NCBIScraper(BasePaginationPublisherScraper):
    @property
    def config_model_type(self) -> Type[NCBIConfig]:
        """
        Return the configuration model type.

        Returns:
            Type[NCBIConfig]: The configuration model type
        """
        return NCBIConfig

    def scrape(self, model: NCBIConfig) -> BasePaginationPublisherScrapeOutput | None:
        """
        Scrape the NCBI sources for PDF links.

        Args:
            model (NCBIConfig): The configuration model.

        Returns:
            BasePaginationPublisherScrapeOutput | None: The output of the scraping, i.e., a dictionary containing the PDF links. Each key is the name of the source which PDF links have been found for, and the value is the list of PDF links itself.
        """
        pdf_tags = []
        for idx, source in enumerate(model.sources):
            self._scrape_landing_page(source.landing_page_url, idx + 1)
            pdf_tags.extend(self._scrape_pagination(source.pagination_url, idx + 1))

        return {"NCBI": [get_scraped_url(tag, self.base_url) for tag in pdf_tags]} if pdf_tags else None

    def _scrape_landing_page(self, landing_page_url: str, source_number: int) -> None:
        """
        Scrape the landing page.

        Args:
            landing_page_url (str): The landing page to scrape.
        """
        self._logger.info(f"Processing Landing Page {landing_page_url}")
        self._scrape_url(landing_page_url)

    def _scrape_page(self, url: str) -> ResultSet | None:
        """
        Scrape the PubMed / NCBI page of the collection from pagination for PDF links.

        Args:
            url (str): The URL to scrape.

        Returns:
            ResultSet | None: A ResultSet (i.e., a list) containing the tags to the PDF links. If something went wrong, return None.
        """
        try:
            scraper = self._scrape_url(url)

            # Find all PDF links using appropriate class or tag (if lambda returns True, it will be included in the list)
            pdf_tag_list = scraper.find_all("a", href=lambda href: href and "/articles/" in href and ".pdf" in href, class_="view")

            self._logger.debug(f"PDF links found: {len(pdf_tag_list)}")
            return pdf_tag_list
        except Exception as e:
            self._logger.error(f"Failed to process URL {url}. Error: {e}")
            return None
