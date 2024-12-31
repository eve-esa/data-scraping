from typing import Type, List
from bs4 import ResultSet, Tag

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

    def scrape(self, model: SageConfig) -> List[Tag] | None:
        """
        Scrape the Sage sources for PDF links.

        Args:
            model (SageConfig): The configuration model.

        Returns:
            List[Tag] | None: A list of Tag objects containing the tags to the PDF links. If no tag was found, return None.
        """
        pdf_tags = []
        for idx, source in enumerate(model.sources):
            pdf_tags.extend(self._scrape_landing_page(source.landing_page_url, idx + 1))

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

        return self._scrape_pagination(landing_page_url, source_number, starting_page_number=0)

    def _scrape_page(self, url: str) -> List[Tag] | None:
        """
        Scrape the PubMed page of the collection from pagination for PDF links.

        Args:
            url (str): The URL to scrape.

        Returns:
            List[Tag] | None: A list of Tag objects containing the tags to the PDF links. If something went wrong, return None.
        """
        try:
            scraper = self._scrape_url_by_bs4(url)

            # Find all article links in the pagination URL, using the appropriate class or tag (if lambda returns True, it will be included in the list)
            articles_links = [get_scraped_url(tag, self.base_url) for tag in scraper.find_all(
                "a", href=lambda href: href and "/doi/reader" in href, data_id="srp-article-button",
            )]

            # Now, visit each article link and find the PDF link
            pdf_tag_list = [
                Tag(name="a", attrs={"href": tag.get("href", "").replace("?download=true", "")})
                for article_link in articles_links
                if (tag := self._scrape_url_by_bs4(article_link).find(
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
