from typing import List, Type
from bs4 import Tag, ResultSet

from helper.utils import get_scraped_url
from model.base_pagination_publisher_models import BasePaginationPublisherConfig, BasePaginationPublisherScrapeOutput
from scraper.base_pagination_publisher_scraper import BasePaginationPublisherScraper


class CambridgeUniversityPressScraper(BasePaginationPublisherScraper):
    @property
    def config_model_type(self) -> Type[BasePaginationPublisherConfig]:
        """
        Return the configuration model type.

        Returns:
            Type[BasePaginationPublisherConfig]: The configuration model type
        """
        return BasePaginationPublisherConfig

    def scrape(self) -> BasePaginationPublisherScrapeOutput | None:
        """
        Scrape the Cambridge University Press sources for PDF links.

        Returns:
            BasePaginationPublisherScrapeOutput: The output of the scraping, i.e., a dictionary containing the PDF links. Each key is the name of the source which PDF links have been found for, and the value is the list of PDF links itself.
        """
        pdf_links = [
            get_scraped_url(pdf_tag, self._config_model.base_url)
            for idx, source in enumerate(self._config_model.sources)
            for tag in self._scrape_landing_page(source.landing_page_url, idx + 1)
            for pdf_tag in self._scrape_pagination(
                f"{get_scraped_url(tag, self._config_model.base_url)}?pageNum={{page_number}}",
                idx + 1
            )
        ]

        return {"Cambridge University Press": pdf_links} if pdf_links else None

    def _scrape_landing_page(self, landing_page_url: str, source_number: int) -> ResultSet | List[Tag]:
        """
        Scrape the landing page.

        Args:
            landing_page_url (str): The landing page to scrape.

        Returns:
            List[Tag]: A list of Tag objects containing the tags to the PDF links. If something went wrong, an empty list.
        """
        self._logger.info(f"Processing Landing Page {landing_page_url}")

        try:
            scraper, driver = self._scrape_url(landing_page_url)
            driver.quit()

            # Find all PDF links using appropriate class or tag (if lambda returns True, it will be included in the list)
            return scraper.find_all("a", href=lambda href: href and "/core/" in href and "/issue/" in href, class_="row")
        except Exception as e:
            self._log_and_save_failure(landing_page_url, f"Failed to process URL {landing_page_url}. Error: {e}")
            return []

    def _scrape_page(self, url: str) -> ResultSet | None:
        """
        Scrape the Cambridge University Press page of the collection from pagination for PDF links.

        Args:
            url (str): The URL to scrape.

        Returns:
            ResultSet | None: A ResultSet (i.e., a list) containing the tags to the PDF links. If something went wrong, return None.
        """
        try:
            scraper, driver = self._scrape_url(url)
            driver.quit()

            # Find all PDF links using appropriate class or tag (if lambda returns True, it will be included in the list)
            if not (pdf_tag_list := scraper.find_all("a", href=lambda href: href and ".pdf" in href)):
                self._save_failure(url)

            self._logger.debug(f"PDF links found: {len(pdf_tag_list)}")
            return pdf_tag_list
        except Exception as e:
            self._log_and_save_failure(url, f"Failed to process URL {url}. Error: {e}")
            return None
