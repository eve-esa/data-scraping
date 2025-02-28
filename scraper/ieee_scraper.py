from typing import List, Type
from bs4 import Tag, ResultSet

from helper.utils import get_scraped_url_by_bs_tag
from model.base_pagination_publisher_models import BasePaginationPublisherScrapeOutput, BasePaginationPublisherConfig
from scraper.base_pagination_publisher_scraper import BasePaginationPublisherScraper
from scraper.base_source_download_scraper import BaseSourceDownloadScraper


class IEEEScraper(BasePaginationPublisherScraper, BaseSourceDownloadScraper):
    def __init__(self):
        super().__init__()
        self.__source = None

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
        Scrape the IEEE sources for PDF links.

        Returns:
            BasePaginationPublisherScrapeOutput | None: The output of the scraping, i.e., a dictionary containing the PDF links. Each key is the name of the source which PDF links have been found for, and the value is the list of PDF links itself.
        """
        pdf_links = []
        for idx, source in enumerate(self._config_model.sources):
            self.__source = source
            pdf_links.extend([
                get_scraped_url_by_bs_tag(pdf_tag, self._config_model.base_url, with_querystring=True)
                for pdf_tag in self._scrape_landing_page(source.landing_page_url, idx + 1)
            ])

        return {"IEEE": pdf_links} if pdf_links else None

    def _scrape_landing_page(self, landing_page_url: str, source_number: int) -> List[Tag]:
        """
        Scrape the landing page.

        Args:
            landing_page_url (str): The landing page to scrape.

        Returns:
            List[Tag]: A list of Tag objects containing the tags to the PDF links. If something went wrong, an empty list.
        """
        self._logger.info(f"Processing Landing Page {landing_page_url}")

        return self._scrape_pagination(
            landing_page_url,
            source_number,
            page_size=self.__source.page_size,
            max_allowed_papers=self.__source.max_allowed_papers
        )

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

    def _get_file_path_from_link(self, link: str) -> str | None:
        file_path = None
        try:
            # visit the PDF link
            self._driver.cdp.open(link)

            # get the iframe source, which is the real PDF link to download
            scraper = self._get_parsed_page_source()
            pdf_url = scraper.find("iframe", src=True, sandbox=False).get("src")
            self._driver.cdp.open(pdf_url)

            file_path = self._wait_end_download(".pdf")
        except Exception as e:
            self._logger.error(f"Error uploading to S3: {e}")
        finally:
            return file_path
