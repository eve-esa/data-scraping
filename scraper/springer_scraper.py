from typing import List, Dict, Type
from bs4 import ResultSet, Tag

from helper.utils import get_scraped_url_by_bs_tag, get_scraped_url_by_web_element, get_ancestor
from model.base_mapped_models import BaseMappedUrlSource, BaseMappedPaginationConfig, BaseMappedUrlConfig
from model.base_pagination_publisher_models import BasePaginationPublisherScrapeOutput
from scraper.base_mapped_publisher_scraper import BaseMappedPublisherScraper
from scraper.base_pagination_publisher_scraper import BasePaginationPublisherScraper
from scraper.base_scraper import BaseMappedSubScraper
from scraper.base_url_publisher_scraper import BaseUrlPublisherScraper, SourceType


class SpringerScraper(BaseMappedPublisherScraper):
    @property
    def mapping(self) -> Dict[str, Type[BaseMappedSubScraper]]:
        return {
            "SpringerUrlScraper": SpringerUrlScraper,
            "SpringerSearchEngineScraper": SpringerSearchEngineScraper,
        }


class SpringerUrlScraper(BaseUrlPublisherScraper, BaseMappedSubScraper):
    @property
    def config_model_type(self) -> Type[BaseMappedUrlConfig]:
        return BaseMappedUrlConfig

    def _scrape_journal(self, source: BaseMappedUrlSource) -> List[Tag] | None:
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

        # For each tag of articles previously collected, scrape the article
        pdf_tag_list = [
            tag
            for tag in (
                self._scrape_article(BaseMappedUrlSource(
                    url=get_scraped_url_by_bs_tag(tag, self._config_model.base_url), type=str(SourceType.ARTICLE)
                ))
                for tag in article_tag_list
            )
            if tag
        ]

        self._logger.debug(f"PDF links found: {len(pdf_tag_list)}")
        return pdf_tag_list

    def _scrape_issue_or_collection(self, source: BaseMappedUrlSource) -> ResultSet | None:
        self._logger.info(f"Processing Issue / Collection {source.url}")

        try:
            scraper = self._scrape_url(source.url)

            # Find all PDF links using appropriate class or tag (if lambda returns True, it will be included in the list)
            if not (pdf_tag_list := scraper.find_all("a", href=lambda href: href and "/pdf/" in href)):
                self._save_failure(source.url)

            self._logger.debug(f"PDF links found: {len(pdf_tag_list)}")
            return pdf_tag_list
        except Exception as e:
            self._log_and_save_failure(source.url, f"Failed to process Issue / Collection {source.url}. Error: {e}")
            return None

    def _scrape_article(self, source: BaseMappedUrlSource) -> Tag | None:
        self._logger.info(f"Processing Article {source.url}")

        try:
            scraper = self._scrape_url(source.url)

            # Find the PDF link using appropriate class or tag (if lambda returns True, it will be included in the list)
            if not (tag := scraper.find("a", href=lambda href: href and "/pdf/" in href)):
                self._save_failure(source.url)

            return tag
        except Exception as e:
            self._log_and_save_failure(source.url, f"Failed to process Article {source.url}. Error: {e}")
            return None


class SpringerSearchEngineScraper(BasePaginationPublisherScraper, BaseMappedSubScraper):
    def __init__(self):
        super().__init__()
        self.__max_consecutive_failures = 5
        self.__consecutive_failures = 0

    @property
    def config_model_type(self) -> Type[BaseMappedPaginationConfig]:
        return BaseMappedPaginationConfig

    def scrape(self) -> BasePaginationPublisherScrapeOutput | None:
        pdf_tags = []
        for idx, source in enumerate(self._config_model.sources):
            self.__consecutive_failures = 0
            pdf_tags.extend(self._scrape_landing_page(source.landing_page_url, idx + 1))

        return {"Springer": [
            get_scraped_url_by_bs_tag(tag, self._config_model.base_url) for tag in pdf_tags
        ]} if pdf_tags else None

    def _scrape_landing_page(self, landing_page_url: str, source_number: int) -> List[Tag]:
        return self._scrape_pagination(landing_page_url, source_number)

    def _is_valid_tag_list(self, page_tag_list: List | None) -> bool:
        return page_tag_list is not None and self.__consecutive_failures <= self.__max_consecutive_failures

    def _scrape_page(self, url: str) -> List[Tag] | None:
        try:
            self._scrape_url(url)

            try:
                tags = self._driver.cdp.find_all("svg.app-entitlement__icon--full-access", timeout=0.5)
            except:
                tags = []

            articles_links = [
                get_scraped_url_by_web_element(a_tag, self._config_model.base_url)
                for tag in tags
                if (ancestor := get_ancestor(tag, "div.app-card-open__main"))
                   and (a_tag := ancestor.query_selector("a.app-card-open__link"))
            ]

            if not articles_links:
                self.__consecutive_failures += 1
                self._save_failure(url)

            pdf_tag_list = [
                Tag(name="a", attrs={
                    "href": link.replace("/article/", "/content/pdf/").replace(
                        "/chapter/", "/content/pdf/"
                    ).replace("/book/", "/content/pdf/")
                })
                for link in articles_links
            ]

            self._logger.debug(f"PDF links found: {len(pdf_tag_list)}")
            return pdf_tag_list
        except Exception as e:
            self._log_and_save_failure(url, f"Failed to process URL {url}. Error: {e}")
            return None
