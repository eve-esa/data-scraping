from typing import Type, List
from bs4 import ResultSet, Tag

from helper.utils import get_scraped_url_by_bs_tag, get_scraped_url_by_web_element, get_ancestor
from model.base_pagination_publisher_models import BasePaginationPublisherScrapeOutput
from model.wiley_models import WileyConfig
from scraper.base_pagination_publisher_scraper import BasePaginationPublisherScraper


class WileyScraper(BasePaginationPublisherScraper):
    def __init__(self):
        super().__init__()
        self.__source = None

    @property
    def config_model_type(self) -> Type[WileyConfig]:
        """
        Return the configuration model type.

        Returns:
            Type[WileyConfig]: The configuration model type
        """
        return WileyConfig

    def scrape(self) -> BasePaginationPublisherScrapeOutput | None:
        """
        Scrape the Sage sources for PDF links.

        Returns:
            BasePaginationPublisherScrapeOutput | None: The output of the scraping, i.e., a dictionary containing the PDF links. Each key is the name of the source which PDF links have been found for, and the value is the list of PDF links itself.
        """
        pdf_tags = {}
        for idx, source in enumerate(self._config_model.sources):
            self.__source = source
            pdf_tags_journal = self._scrape_landing_page(source.landing_page_url, idx + 1)
            if pdf_tags_journal:
                pdf_tags[source.name] = [get_scraped_url_by_bs_tag(tag, source.base_url) for tag in pdf_tags_journal]

        return pdf_tags if pdf_tags else None

    def _scrape_landing_page(self, landing_page_url: str, source_number: int) -> List[Tag]:
        """
        Scrape the landing page.

        Args:
            landing_page_url (str): The landing page to scrape.

        Returns:
            List[Tag]: A list of Tag objects containing the tags to the PDF links. If something went wrong, an empty list.
        """
        self._logger.info(f"Processing Landing Page {landing_page_url}")

        return self._scrape_pagination(landing_page_url, source_number, base_zero=True, page_size=self.__source.page_size)

    def _scrape_page(self, url: str) -> List[Tag] | None:
        """
        Scrape the PubMed page of the collection from pagination for PDF links.

        Args:
            url (str): The URL to scrape.

        Returns:
            ResultSet | None: A ResultSet (i.e., a list) containing the tags to the PDF links. If something went wrong, return None.
        """
        try:
            self._scrape_url(url)

            try:
                tags = self._driver.cdp.find_all("i.icon-icon-lock_open")
            except:
                tags = []

            if not (articles_links := [
                get_scraped_url_by_web_element(a_tag, self.__source.base_url).replace("/doi/", "/doi/pdfdirect/")
                for tag in tags
                if (ancestor := get_ancestor(tag, "div.item__body"))
                   and (a_tag := ancestor.query_selector("a.publication_title.visitable"))
                   and (href := a_tag.get_attribute("href"))
                   and "/doi/" in href
            ]):
                self._save_failure(url)

            self._logger.debug(f"PDF links found: {len(articles_links)}")
            return [Tag(name="a", attrs={"href": link}) for link in articles_links]
        except Exception as e:
            self._log_and_save_failure(url, f"Failed to process URL {url}. Error: {e}")
            return None
