from typing import List, Dict, Type
from bs4 import ResultSet, Tag
from selenium.webdriver.common.by import By

from helper.utils import get_scraped_url
from model.base_mapped_models import BaseMappedUrlSource, BaseMappedPaginationConfig
from model.base_pagination_publisher_models import BasePaginationPublisherScrapeOutput
from scraper.base_mapped_publisher_scraper import BaseMappedPublisherScraper
from scraper.base_pagination_publisher_scraper import BasePaginationPublisherScraper
from scraper.base_scraper import BaseMappedScraper
from scraper.base_url_publisher_scraper import BaseUrlPublisherScraper, SourceType


class SpringerScraper(BaseMappedPublisherScraper):
    @property
    def mapping(self) -> Dict[str, Type[BaseMappedScraper]]:
        return {
            "SpringerUrlScraper": SpringerUrlScraper,
            "SpringerSearchEngineScraper": SpringerSearchEngineScraper,
        }


class SpringerUrlScraper(BaseUrlPublisherScraper, BaseMappedScraper):
    def _scrape_journal(self, source: BaseMappedUrlSource) -> List[Tag] | None:
        """
        Scrape all articles of a journal.

        Args:
            source (BaseMappedUrlSource): The journal to scrape.

        Returns:
            List[Tag] | None: A list of Tag objects containing the PDF links. If no tag was found, return None.
        """
        self._logger.info(f"Processing Journal {source.url}")

        # navigate through the pagination of the journal
        counter = 1
        article_tag_list = []
        while True:
            try:
                scraper = self._scrape_url(f"{source.url}?filterOpenAccess=false&page={counter}")

                # Find all PDF links using appropriate class or tag (if lambda returns True, it will be included in the list)
                tags = scraper.find_all("a", href=lambda href: href and "/article/" in href)
                if len(tags) == 0:
                    break

                article_tag_list.extend(tags)
                counter += 1
            except Exception as e:
                self._logger.error(f"Failed to process Journal {source.url}. Error: {e}")
                break
        try:
            # For each tag of articles previously collected, scrape the article
            pdf_tag_list = [
                tag for tag in (
                    self._scrape_article(
                        BaseMappedUrlSource(url=get_scraped_url(tag, self.base_url), type=str(SourceType.ARTICLE))
                    )
                    for tag in article_tag_list
                ) if tag
            ]
            self._logger.info(f"PDF links found: {len(pdf_tag_list)}")

            return pdf_tag_list
        except Exception as e:
            self._logger.error(f"Failed to process Journal {source.url}. Error: {e}")
            return None

    def _scrape_issue_or_collection(self, source: BaseMappedUrlSource) -> ResultSet | None:
        """
        Scrape the issue (or collection) URL for PDF links.

        Args:
            source (BaseMappedUrlSource): The issue / collection to scrape.

        Returns:
            ResultSet | None: A ResultSet (i.e., list) object containing the tags to the PDF links, or None if no tag was found.
        """
        self._logger.info(f"Processing Issue / Collection {source.url}")

        try:
            scraper = self._scrape_url(source.url)

            # Find all PDF links using appropriate class or tag (if lambda returns True, it will be included in the list)
            pdf_tag_list = scraper.find_all("a", href=lambda href: href and "/pdf/" in href)
            self._logger.info(f"PDF links found: {len(pdf_tag_list)}")

            return pdf_tag_list
        except Exception as e:
            self._logger.error(f"Failed to process Issue / Collection {source.url}. Error: {e}")
            return None

    def _scrape_article(self, source: BaseMappedUrlSource) -> Tag | None:
        """
        Scrape a single article.

        Args:
            source (BaseMappedUrlSource): The article to scrape.

        Returns:
            Tag | None: The tag containing the PDF link found in the article, or None if no tag was found.
        """
        self._logger.info(f"Processing Article {source.url}")

        try:
            scraper = self._scrape_url(source.url)

            # Find the PDF link using appropriate class or tag (if lambda returns True, it will be included in the list)
            return scraper.find("a", href=lambda href: href and "/pdf/" in href)
        except Exception as e:
            self._logger.error(f"Failed to process Article {source.url}. Error: {e}")
            return None


class SpringerSearchEngineScraper(BasePaginationPublisherScraper, BaseMappedScraper):
    @property
    def config_model_type(self) -> Type[BaseMappedPaginationConfig]:
        """
        Return the configuration model type.

        Returns:
            Type[BaseMappedPaginationConfig]: The configuration model type
        """
        return BaseMappedPaginationConfig

    def scrape(self, model: BaseMappedPaginationConfig) -> BasePaginationPublisherScrapeOutput | None:
        """
        Scrape the Springer sources from Search Engine tools for PDF links.

        Args:
            model (BaseMappedPaginationConfig): The configuration model.

        Returns:
            BasePaginationPublisherScrapeOutput: The output of the scraping, i.e., a dictionary containing the PDF links. Each key is the name of the source which PDF links have been found for, and the value is the list of PDF links itself.
        """
        pdf_tags = []
        for idx, source in enumerate(model.sources):
            pdf_tags.extend(self._scrape_landing_page(source.landing_page_url, idx + 1))

        return {"Springer": [get_scraped_url(tag, self.base_url) for tag in pdf_tags]} if pdf_tags else None

    def _scrape_landing_page(self, landing_page_url: str, source_number: int) -> ResultSet | List[Tag]:
        """
        Scrape the landing page.

        Args:
            landing_page_url (str): The landing page to scrape.

        Returns:
            List[Tag]: A list of Tag objects containing the tags to the PDF links. If something went wrong, an empty list.
        """
        self._logger.info(f"Processing Landing Page {landing_page_url}")

        return self._scrape_pagination(landing_page_url, source_number)

    def _check_tag_list(self, page_tag_list):
        return page_tag_list is not None

    def _scrape_page(self, url: str) -> List[Tag] | None:
        """
        Scrape the Cambridge University Press page of the collection from pagination for PDF links.

        Args:
            url (str): The URL to scrape.

        Returns:
            ResultSet | None: A ResultSet (i.e., a list) containing the tags to the PDF links. If something went wrong, return None.
        """
        try:
            scraper = self._scrape_url(url)

            article_tag_list = scraper.find_all("a", href=True, class_="app-card-open__link")
            if not article_tag_list:
                return None

            # by using Selenium self._driver, search for all "a" tags, with class "app-card-open__link", href attribute and which parent has the previous sibling:
            # - with class "app-entitlement"
            # - containing a svg with class "app-entitlement__icon.app-entitlement__icon--full-access
            open_access_article_tag_list = self._driver.find_elements(
                By.XPATH,
                "//a[contains(@class, 'app-card-open__link')]/parent::h3/preceding-sibling::div[contains(@class, 'app-entitlement') and .//svg[contains(@class, 'app-entitlement__icon--full-access')]]"
            )

            scrapers = [
                self._scrape_url(get_scraped_url(Tag(name="a", attrs={"href": tag["href"]}), self.base_url))
                for tag in open_access_article_tag_list
            ]

            pdf_tag_list = [
                pdf_tag
                for scraper in scrapers
                if (pdf_tag := scraper.find(
                    "a",
                    href=lambda href: href and ".pdf" in href,
                    class_=lambda class_: class_ and "c-pdf-download__link" in class_))
            ]

            self._logger.info(f"PDF links found: {len(pdf_tag_list)}")
            return pdf_tag_list
        except Exception as e:
            self._logger.error(f"Failed to process URL {url}. Error: {e}")
            return None
