from typing import Type, List
from bs4 import ResultSet, Tag
from selenium.webdriver.common.by import By

from helper.utils import get_scraped_url, get_link_for_accessible_article, remove_query_string_from_url
from model.base_pagination_publisher_models import BasePaginationPublisherScrapeOutput
from model.wiley_models import WileyConfig
from scraper.base_pagination_publisher_scraper import BasePaginationPublisherScraper


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

    def scrape(self) -> BasePaginationPublisherScrapeOutput | None:
        """
        Scrape the Sage sources for PDF links.

        Returns:
            BasePaginationPublisherScrapeOutput | None: The output of the scraping, i.e., a dictionary containing the PDF links. Each key is the name of the source which PDF links have been found for, and the value is the list of PDF links itself.
        """
        pdf_tags = {}
        for idx, source in enumerate(self._config_model.sources):
            self.__base_url = source.base_url
            pdf_tags_journal = self._scrape_landing_page(source.landing_page_url, idx + 1)
            if pdf_tags_journal:
                pdf_tags[source.name] = [get_scraped_url(tag, self.__base_url) for tag in pdf_tags_journal]

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

        return self._scrape_pagination(landing_page_url, source_number, base_zero=True)

    def _scrape_page(self, url: str) -> List[Tag] | None:
        """
        Scrape the PubMed page of the collection from pagination for PDF links.

        Args:
            url (str): The URL to scrape.

        Returns:
            ResultSet | None: A ResultSet (i.e., a list) containing the tags to the PDF links. If something went wrong, return None.
        """
        try:
            _, driver = self._scrape_url(url)

            # Find all article links in the pagination URL, using the appropriate class or tag (if lambda returns True, it will be included in the list)
            article_tags = driver.find_elements(
                By.XPATH,
                "//a[contains(@class, 'publication_title') and contains(@class, 'visitable') and contains(@href, '/doi/')]"
            )
            driver.quit()

            articles_links = [
                link
                for article_tag in article_tags
                if (link := get_link_for_accessible_article(
                    article_tag,
                    self.__base_url,
                    "../../preceding-sibling::div[contains(@class, 'meta__header')]//i[contains(@class, 'icon-icon-lock_open')]"
                ))
            ]

            # Now, visit each article link and find the PDF link
            pdf_tag_list = [
                tag for article_link in articles_links if (tag := self.__scrape_article(article_link))
            ]

            self._logger.debug(f"PDF links found: {len(pdf_tag_list)}")
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
        self._logger.info(f"Processing Article {url}")

        try:
            scraper, driver = self._scrape_url(url)
            driver.quit()

            # look for the ePDF link in the article page
            epdf_tag = scraper.find(
                "a",
                href=lambda href: href and "/doi/epdf/" in href,
                class_=lambda class_: class_ and "pdf-download" in class_,
            )
            if not epdf_tag:
                return None

            # now, scrape the ePDF page to get the final PDF link, and return this latter tag
            scraper, driver = self._scrape_url(get_scraped_url(epdf_tag, self.__base_url))
            driver.quit()

            if not (direct_pdf_tag := scraper.find("a", href=lambda href: href and "/doi/pdfdirect/" in href)):
                return None

            return Tag(name="a", attrs={"href": remove_query_string_from_url(direct_pdf_tag.get("href"))})
        except Exception as e:
            self._logger.error(f"Failed to process URL {url}. Error: {e}")
            return None
