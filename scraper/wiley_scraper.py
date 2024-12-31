from typing import Type, List
from bs4 import ResultSet, Tag

from model.wiley_models import WileyConfig
from scraper.base_pagination_publisher_scraper import BasePaginationPublisherScraper
from utils import get_scraped_url


class WileyScraper(BasePaginationPublisherScraper):
    def __init__(self):
        super().__init__()
        self.__base_url = None

    @property
    def config_model_type(self) -> Type[WileyConfig]:
        """
        Return the configuration model type.

        Returns:
            Type[WileyConfig]: The configuration model type
        """
        return WileyConfig

    def scrape(self, model: WileyConfig) -> List[Tag] | None:
        """
        Scrape the Sage sources for PDF links.

        Args:
            model (WileyConfig): The configuration model.

        Returns:
            List[Tag] | None: A list of Tag objects containing the tags to the PDF links. If no tag was found, return None.
        """
        pdf_tags = []
        for idx, source in enumerate(model.sources):
            self.__base_url = source.base_url
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
            ResultSet | None: A ResultSet (i.e., a list) containing the tags to the PDF links. If something went wrong, return None.
        """
        try:
            scraper = self._scrape_url_by_bs4(url)

            # Find all article links in the pagination URL, using the appropriate class or tag (if lambda returns True, it will be included in the list)
            articles_links = [get_scraped_url(tag, self.__base_url) for tag in scraper.find_all(
                "a",
                href=lambda href: href and "/doi/" in href,
                class_=lambda class_: class_ and "publication_title" in class_ and "visitable" in class_,
            )]

            # Now, visit each article link and find the PDF link
            pdf_tag_list = [tag for article_link in articles_links if (tag := self.__scrape_article(article_link))]

            self._logger.info(f"PDF links found: {len(pdf_tag_list)}")
            return pdf_tag_list
        except Exception as e:
            self._logger.error(f"Failed to process URL {url}. Error: {e}")
            return None

    def __scrape_article(self, url: str) -> Tag | None:
        """
        Scrape the article page of the collection for the PDF link.

        Args:
            url (str): The URL to scrape.

        Returns:
            Tag | None: A Tag object containing the tag to the PDF link. If something went wrong, return None.
        """
        try:
            scraper = self._scrape_url_by_bs4(url)

            # look for the ePDF link in the article page
            epdf_tag = scraper.find(
                "a",
                href=lambda href: href and "/doi/epdf/" in href,
                class_=lambda class_: class_ and "pdf-download" in class_,
            )
            if not epdf_tag:
                return None

            # now, scrape the ePDF page to get the final PDF link, and return this latter tag
            direct_pdf_tag = self._scrape_url_by_bs4(
                get_scraped_url(epdf_tag, self.__base_url)
            ).find("a", href=lambda href: href and "/doi/pdfdirect/" in href)
            if not direct_pdf_tag:
                return None

            return Tag(name="a", attrs={"href": direct_pdf_tag.get("href").replace("?download=true", "")})
        except Exception as e:
            self._logger.error(f"Failed to process URL {url}. Error: {e}")
            return None
