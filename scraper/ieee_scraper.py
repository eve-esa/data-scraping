from typing import List, Type, Dict
from bs4 import Tag, ResultSet

from helper.utils import get_scraped_url_by_bs_tag
from model.base_mapped_models import BaseMappedPaginationConfig
from model.base_pagination_publisher_models import BasePaginationPublisherScrapeOutput
from scraper.base_mapped_publisher_scraper import BaseMappedPublisherScraper
from scraper.base_pagination_publisher_scraper import BasePaginationPublisherScraper
from scraper.base_scraper import BaseMappedSubScraper, BaseScraper


class IEEEScraper(BaseMappedPublisherScraper):
    @property
    def mapping(self) -> Dict[str, Type[BaseMappedSubScraper]]:
        return {
            "IEEEJournalsScraper": IEEEJournalsScraper,
            "IEEESearchScraper": IEEESearchScraper,
        }


class IEEEJournalsScraper(BasePaginationPublisherScraper, BaseMappedSubScraper):
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
            get_scraped_url_by_bs_tag(pdf_tag, self._config_model.base_url)
            for idx, source in enumerate(self._config_model.sources)
            for tag in self._scrape_landing_page(source.landing_page_url, idx + 1)
            for pdf_tag in self._scrape_pagination(
                f"{get_scraped_url_by_bs_tag(tag, self._config_model.base_url, with_querystring=True)}&sortType=vol-only-seq&rowsPerPage=100&pageNumber={{page_number}}",
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
        waited_tag = self._config_model.waited_tag

        try:
            self._config_model.waited_tag = None
            self._scrape_url(landing_page_url)

            tag_links = self._driver.cdp.find_elements("div.issue-details-past-tabs a", timeout=20)

            tags = []
            for tag_link in tag_links:
                href = tag_link.get_attribute("href")  # the link represents a page of the collection
                if href and "/tocresult" in href and "punumber=" in href:
                    tags.append(Tag(name="a", attrs={"href": tag_link.get_attribute("href")}))
                elif href is None:  # the link represents a falsy button to click on, to load the list of various issues
                    tag_link.click()
                    self._driver.cdp.sleep(0.1)
                    tags.extend([
                        Tag(name="a", attrs={"href": href})
                        for tag in self._driver.cdp.find_elements("div.issue-list a")
                        if (href := tag.get_attribute("href")) and "/tocresult" in href and "punumber=" in href
                    ])

            # Find all PDF links using appropriate class or tag (if lambda returns True, it will be included in the list)
            if not tags:
                self._save_failure(landing_page_url)

            self._config_model.waited_tag = waited_tag
            return tags
        except Exception as e:
            self._log_and_save_failure(landing_page_url, f"Failed to process URL {landing_page_url}. Error: {e}")
            self._config_model.waited_tag = waited_tag
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
            scraper = self._scrape_url(url)

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


class IEEESearchScraper(BasePaginationPublisherScraper, BaseMappedSubScraper):
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
            get_scraped_url_by_bs_tag(pdf_tag, self._config_model.base_url)
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
            scraper = self._scrape_url(url)

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
