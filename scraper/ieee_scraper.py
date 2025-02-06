from abc import ABC
from typing import List, Type, Dict
from bs4 import Tag, ResultSet
from selenium.webdriver.support.wait import WebDriverWait
from seleniumbase import Driver

from helper.utils import get_scraped_url
from model.base_mapped_models import BaseMappedPaginationConfig
from model.base_pagination_publisher_models import BasePaginationPublisherScrapeOutput
from scraper.base_mapped_publisher_scraper import BaseMappedPublisherScraper
from scraper.base_pagination_publisher_scraper import BasePaginationPublisherScraper
from scraper.base_scraper import BaseMappedScraper, BaseScraper


class IEEEMixin(BaseScraper, ABC):
    def _wait_for_page_load(self, driver: Driver, timeout: int | None = 20):
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
                      and not d.execute_script("return document.querySelector('i.fa-spinner')")
        )


class IEEEScraper(BaseMappedPublisherScraper):
    @property
    def mapping(self) -> Dict[str, Type[BaseMappedScraper]]:
        return {
            "IEEEJournalsScraper": IEEEJournalsScraper,
            "IEEESearchScraper": IEEESearchScraper,
        }


class IEEEJournalsScraper(BasePaginationPublisherScraper, BaseMappedScraper, IEEEMixin):
    @property
    def config_model_type(self) -> Type[BaseMappedPaginationConfig]:
        """
        Return the configuration model type.

        Returns:
            Type[BaseMappedPaginationConfig]: The configuration model type
        """
        return BaseMappedPaginationConfig

    def scrape(self) -> BasePaginationPublisherScrapeOutput | None:
        """
        Scrape the IEEE sources for PDF links.

        Returns:
            BasePaginationPublisherScrapeOutput | None: The output of the scraping, i.e., a dictionary containing the PDF links. Each key is the name of the source which PDF links have been found for, and the value is the list of PDF links itself.
        """
        pdf_links = [
            get_scraped_url(pdf_tag, self._config_model.base_url)
            for idx, source in enumerate(self._config_model.sources)
            for tag in self._scrape_landing_page(source.landing_page_url, idx + 1)
            for pdf_tag in self._scrape_pagination(
                f"{get_scraped_url(tag, self._config_model.base_url, with_querystring=True)}&sortType=vol-only-seq&rowsPerPage=100&pageNumber={{page_number}}",
                idx + 1
            )
        ]

        return {"IEEE": pdf_links} if pdf_links else None

    def _scrape_landing_page(self, landing_page_url: str, source_number: int) -> ResultSet | List[Tag]:
        """
        Scrape the landing page.

        Args:
            landing_page_url (str): The landing page to scrape.

        Returns:
            ResultSet | List[Tag]: A ResultSet (i.e., a list) or a list of Tag objects containing the tags to the PDF links. If something went wrong, an empty list.
        """
        self._logger.info(f"Processing Landing Page {landing_page_url}")

        try:
            scraper, driver = self._scrape_url(landing_page_url)
            driver.quit()

            # Find all PDF links using appropriate class or tag (if lambda returns True, it will be included in the list)
            if not (tags := scraper.find_all("a", href=lambda href: href and "/tocresult" in href and "punumber=" in href)):
                self._save_failure(landing_page_url)

            return tags
        except Exception as e:
            self._log_and_save_failure(landing_page_url, f"Failed to process URL {landing_page_url}. Error: {e}")
            return []

    def _scrape_page(self, url: str) -> ResultSet | None:
        """
        Scrape the IEEE page of the collection from pagination for PDF links.

        Args:
            url (str): The URL to scrape.

        Returns:
            ResultSet | None: A ResultSet (i.e., a list) containing the tags to the PDF links. If something went wrong, return None.
        """
        try:
            scraper, driver = self._scrape_url(url)
            driver.quit()

            # Find all PDF links using appropriate class or tag (if lambda returns True, it will be included in the list)
            if not (pdf_tag_list := scraper.find_all(
                "a",
                href=lambda href: href and "/stamp/stamp.jsp" in href,
                class_=lambda class_: class_ and "u-flex-display-flex" in class_
            )):
                self._save_failure(url)

            self._logger.debug(f"PDF links found: {len(pdf_tag_list)}")
            return pdf_tag_list
        except Exception as e:
            self._log_and_save_failure(url, f"Failed to process URL {url}. Error: {e}")
            return None


class IEEESearchScraper(BasePaginationPublisherScraper, BaseMappedScraper, IEEEMixin):
    @property
    def config_model_type(self) -> Type[BaseMappedPaginationConfig]:
        """
        Return the configuration model type.

        Returns:
            Type[BaseMappedPaginationConfig]: The configuration model type
        """
        return BaseMappedPaginationConfig

    def scrape(self) -> BasePaginationPublisherScrapeOutput | None:
        """
        Scrape the IEEE sources for PDF links.

        Returns:
            BasePaginationPublisherScrapeOutput | None: The output of the scraping, i.e., a dictionary containing the PDF links. Each key is the name of the source which PDF links have been found for, and the value is the list of PDF links itself.
        """
        pdf_links = [
            get_scraped_url(pdf_tag, self._config_model.base_url)
            for idx, source in enumerate(self._config_model.sources)
            for pdf_tag in self._scrape_landing_page(source.landing_page_url, idx + 1)
        ]

        return {"IEEE": pdf_links} if pdf_links else None

    def _scrape_landing_page(self, landing_page_url: str, source_number: int) -> ResultSet | List[Tag]:
        """
        Scrape the landing page.

        Args:
            landing_page_url (str): The landing page to scrape.

        Returns:
            ResultSet | List[Tag]: A ResultSet (i.e., a list) or a list of Tag objects containing the tags to the PDF links. If something went wrong, an empty list.
        """
        self._logger.info(f"Processing Landing Page {landing_page_url}")

        return self._scrape_pagination(landing_page_url, source_number)

    def _scrape_page(self, url: str) -> ResultSet | None:
        """
        Scrape the IEEE page of the collection from pagination for PDF links.

        Args:
            url (str): The URL to scrape.

        Returns:
            ResultSet | None: A ResultSet (i.e., a list) containing the tags to the PDF links. If something went wrong, return None.
        """
        try:
            scraper, driver = self._scrape_url(url)
            driver.quit()

            # Find all PDF links using appropriate class or tag (if lambda returns True, it will be included in the list)
            if not (pdf_tag_list := scraper.find_all(
                "a",
                href=lambda href: href and "/stamp/stamp.jsp" in href,
                class_=lambda class_: class_ and "u-flex-display-flex" in class_
            )):
                self._save_failure(url)

            self._logger.debug(f"PDF links found: {len(pdf_tag_list)}")
            return pdf_tag_list
        except Exception as e:
            self._log_and_save_failure(url, f"Failed to process URL {url}. Error: {e}")
            return None
