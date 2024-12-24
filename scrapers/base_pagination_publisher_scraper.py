from abc import abstractmethod
from typing import List, Type
from bs4 import ResultSet, Tag
from pydantic import Field, BaseModel

from scrapers.base_scraper import BaseScraper, BaseConfigScraper


class BasePagePublisherSource(BaseModel):
    """
    Configuration model for the base page publisher scraper source.

    Variables:
        pagination_url (str): The landing URL to scrape
    """
    base_url: str


class BaseLandingPagePublisherSource(BasePagePublisherSource):
    """
    Configuration model for the base landing page publisher scraper source. The model contains the landing URL to scrape
    and whether to store the PDF tags from the landing page. The landing URL is the URL to scrape to get the initial
    pagination URL. The `should_store` variable is a boolean that indicates whether to store the PDF tags from the
    landing page. If `should_store` is True, the PDF tags from the landing page are stored. Otherwise, the PDF tags are
    not stored.

    Variables:
        pagination_url (str): The landing URL to scrape
        should_store (bool): Store the PDF tags from the landing page
    """
    should_store: bool = Field(False, description="Store the PDF tags from the landing page")


class BasePaginationPublisherSource(BasePagePublisherSource):
    """
    Configuration model for the base pagination publisher scraper source. The model contains the landing URL to scrape
    and the pagination URL. The landing URL, if provided, is the URL to scrape to get the initial pagination URL. The
    pagination URL is the URL to scrape to get the PDF links.

    Variables:
        landing_page (BaseLandingPagePublisherSource | None): The landing URL to scrape and whether to store the PDF tags from the landing page
        pagination_url (str): The pagination URL
    """
    landing_page: BaseLandingPagePublisherSource | None = Field(None, description="The landing URL to scrape")


class BasePaginationPublisherConfig(BaseConfigScraper):
    """
    Configuration model for the base pagination publisher scraper. The model contains a list of sources to scrape.

    Variables:
        sources (List[BasePaginationPublisherSource]): A list of sources to scrape
    """
    sources: List[BasePaginationPublisherSource]


class BasePaginationPublisherScraper(BaseScraper):
    @property
    def config_model_type(self) -> Type[BasePaginationPublisherConfig]:
        """
        Return the configuration model type. This method must be implemented in the derived class.

        Returns:
            Type[BasePaginationPublisherConfig]: The configuration model type
        """
        return BasePaginationPublisherConfig

    def scrape(self, model: BasePaginationPublisherConfig) -> ResultSet | List[Tag] | None:
        """
        Scrape the source URLs of for PDF links.

        Args:
            model (BaseUrlPublisherConfig): The configuration model.

        Returns:
            ResultSet | List[Tag]: A ResultSet (i.e., a list) or a list of Tag objects containing the tags to the PDF links. If no tag was found, return None.
        """
        pdf_tags = []
        for idx, source in enumerate(model.sources):
            if source.landing_page:
                pdf_tags.extend(self._scrape_landing_page(source.landing_page))
            pdf_tags.extend(self._scrape_pagination(source, idx + 1))

        return pdf_tags if pdf_tags else None

    def post_process(self, scrape_output: ResultSet | List[Tag]) -> List[str]:
        """
        Extract the href attribute from the links.

        Args:
            scrape_output (ResultSet | List[Tag]): A ResultSet (i.e., a list) or a list of Tag objects containing the tags to the PDF links.

        Returns:
            List[str]: A list of strings containing the PDF links
        """
        return [tag.get("href") for tag in scrape_output]

    def _scrape_landing_page(self, landing_page: BaseLandingPagePublisherSource) -> List[Tag]:
        """
        Scrape the landing page. If the source has a landing page, scrape the landing page for PDF links. If the source
        has a landing page and the `should_store` is True, store the PDF tags from the landing page. Otherwise, return
        an empty list.

        Args:
            landing_page (BaseLandingPagePublisherSource): The landing page to scrape.

        Returns:
            List[Tag]: A list of Tag objects containing the tags to the PDF links, if the source has a landing page and the `should_store` is True. Otherwise, an empty list.
        """
        landing_url = landing_page.pagination_url
        self._logger.info(f"Processing Landing Page {landing_url}")

        pdf_tag_list = self._scrape_page(landing_url)
        if landing_page.should_store:
            return pdf_tag_list

        return []

    def _scrape_pagination(self, source: BasePaginationPublisherSource, source_number: int) -> ResultSet | List[Tag]:
        """
        Scrape the pagination URL for PDF links.

        Args:
            source (BasePaginationPublisherSource): The source to scrape.
            source_number (int): The source number.

        Returns:
            ResultSet | List[Tag]: A ResultSet (i.e., a list) or a list of Tag objects containing the tags to the PDF links.
        """
        pagination_url = source.pagination_url
        self._logger.info(f"Processing Source {pagination_url}")

        page_number = 1

        pdf_tag_list = []
        while True:
            # parse the query with parameters
            # they are enclosed in curly braces, must be replaced with the actual values
            # "page_number" and "source_number" are reserved keywords
            page_url = pagination_url.format(
                **{**source.query_params, "page_number": page_number, "source_number": source_number}
            )

            page_tag_list = self._scrape_page(page_url)
            if not page_tag_list:
                break

            pdf_tag_list.extend(page_tag_list)
            page_number += 1

        return pdf_tag_list

    @abstractmethod
    def _scrape_page(self, url: str) -> ResultSet | List[Tag] | None:
        """
        Scrape the page.

        Args:
            url (str): The URL to scrape.

        Returns:
            ResultSet | List[Tag] | None: A ResultSet (i.e., a list) or a list of Tag objects containing the tags to the PDF links. If something went wrong, return None.
        """
        pass
