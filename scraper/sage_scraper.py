from typing import Type, List
from bs4 import Tag

from helper.utils import get_scraped_url_by_bs_tag
from model.base_pagination_publisher_models import BasePaginationPublisherConfig, BasePaginationPublisherScrapeOutput
from scraper.base_pagination_publisher_scraper import BasePaginationPublisherScraper


class SageScraper(BasePaginationPublisherScraper):
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
        Scrape the Sage sources for PDF links.

        Returns:
            BasePaginationPublisherScrapeOutput | None: The output of the scraping, i.e., a dictionary containing the PDF links. Each key is the name of the source which PDF links have been found for, and the value is the list of PDF links itself.
        """
        pdf_tags = []
        for idx, source in enumerate(self._config_model.sources):
            pdf_tags.extend(self._scrape_landing_page(source.landing_page_url, idx + 1))

        return {"Sage": [
            get_scraped_url_by_bs_tag(tag, self._config_model.base_url) for tag in pdf_tags
        ]} if pdf_tags else None

    def _scrape_landing_page(self, landing_page_url: str, source_number: int) -> List[Tag]:
        """
        Scrape the landing page.

        Args:
            landing_page_url (str): The landing page to scrape.

        Returns:
            List[Tag]: A list of Tag objects containing the tags to the PDF links. If something went wrong, an empty list.
        """
        self._logger.info(f"Processing Landing Page {landing_page_url}")

        return self._scrape_pagination(landing_page_url, source_number, base_zero=True)

    def _scrape_page(self, url: str) -> List[Tag] | None:
        """
        Scrape the Sage page of the collection from pagination for PDF links.

        Args:
            url (str): The URL to scrape.

        Returns:
            List[Tag] | None: A list of Tag objects containing the tags to the PDF links. If something went wrong, return None.
        """
        try:
            scraper = self._scrape_url(url)

            # Find all article links in the pagination URL, using the appropriate class or tag (if lambda returns True, it will be included in the list)
            articles_links = [get_scraped_url_by_bs_tag(tag, self._config_model.base_url) for tag in scraper.find_all(
                "a", href=lambda href: href and "/doi/reader" in href, attrs={"data-id": "srp-article-button"}
            )]

            # Now, visit each article link and find the PDF link
            pdf_tag_list = []
            for article_link in articles_links:
                self._driver.cdp.open(article_link)
                self._driver.cdp.sleep(1)

                if (tag := self._get_parsed_page_source().find(
                        "a",
                        id="favourite-download",
                        href=lambda href: href and "/doi/pdf/" in href,
                        class_=lambda class_: class_ and "download" in class_,
                )):
                    pdf_tag_list.append(tag)

            if not pdf_tag_list:
                self._save_failure(url)

            self._logger.debug(f"PDF links found: {len(pdf_tag_list)}")
            return pdf_tag_list
        except Exception as e:
            self._log_and_save_failure(url, f"Failed to process URL {url}. Error: {e}")
            return None
