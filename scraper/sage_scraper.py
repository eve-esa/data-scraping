from typing import Type, List
from bs4 import Tag

from model.base_pagination_publisher_models import BasePaginationPublisherScrapeOutput
from model.sage_models import SageConfig
from scraper.base_pagination_publisher_scraper import BasePaginationPublisherScraper
from utils import get_scraped_url


class SageScraper(BasePaginationPublisherScraper):
    @property
    def config_model_type(self) -> Type[SageConfig]:
        """
        Return the configuration model type.

        Returns:
            Type[SageConfig]: The configuration model type
        """
        return SageConfig

    def scrape(self, model: SageConfig) -> BasePaginationPublisherScrapeOutput:
        """
        Scrape the Sage sources for PDF links.

        Args:
            model (SageConfig): The configuration model.

        Returns:
            BasePaginationPublisherScrapeOutput: The output of the scraping, i.e., a dictionary containing the PDF links. Each key is the name of the source which PDF links have been found for, and the value is the list of PDF links itself.
        """
        pdf_tags = []
        for idx, source in enumerate(model.sources):
            pdf_tags.extend(self._scrape_landing_page(source.landing_page_url, idx + 1))

        return {"Sage": [get_scraped_url(tag, self.base_url) for tag in pdf_tags]}

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

        return self._scrape_pagination(landing_page_url, source_number, starting_page_number=0)

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
            articles_links = [get_scraped_url(tag, self.base_url) for tag in scraper.find_all(
                "a", href=lambda href: href and "/doi/reader" in href, data_id="srp-article-button",
            )]

            # Now, visit each article link and find the PDF link
            pdf_tag_list = [
                Tag(name="a", attrs={"href": tag.get("href", "").replace("?download=true", "")})
                for article_link in articles_links
                if (tag := self._scrape_url(article_link).find(
                    "a",
                    id="favourite-download",
                    href=lambda href: href and "/doi/pdf/" in href,
                    class_=lambda class_: class_ and "download" in class_,
                ))
            ]

            self._logger.info(f"PDF links found: {len(pdf_tag_list)}")
            return pdf_tag_list
        except Exception as e:
            self._logger.error(f"Failed to process URL {url}. Error: {e}")
            return None
