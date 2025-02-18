from typing import Type, Dict, List
from bs4 import Tag, ResultSet

from model.base_mapped_models import BaseMappedCrawlingConfig, BaseMappedUrlConfig
from model.base_url_publisher_models import BaseUrlPublisherSource
from scraper.base_crawling_scraper import BaseCrawlingScraper
from scraper.base_mapped_publisher_scraper import BaseMappedPublisherScraper
from scraper.base_scraper import BaseMappedSubScraper
from scraper.base_url_publisher_scraper import BaseUrlPublisherScraper


class EUMETSATScraper(BaseMappedPublisherScraper):
    @property
    def mapping(self) -> Dict[str, Type[BaseMappedSubScraper]]:
        return {
            "EUMETSATCrawlingScraper": EUMETSATCrawlingScraper,
            "EUMETSATCaseStudiesScraper": EUMETSATCaseStudiesScraper,
        }


class EUMETSATCrawlingScraper(BaseCrawlingScraper, BaseMappedSubScraper):
    @property
    def config_model_type(self) -> Type[BaseMappedCrawlingConfig]:
        return BaseMappedCrawlingConfig

    @property
    def crawling_folder_path(self) -> str:
        return "eumetsat"


class EUMETSATCaseStudiesScraper(BaseUrlPublisherScraper, BaseMappedSubScraper):
    @property
    def config_model_type(self) -> Type[BaseMappedUrlConfig]:
        return BaseMappedUrlConfig

    def _scrape_journal(self, source: BaseUrlPublisherSource) -> ResultSet | List[Tag] | None:
        pass

    def _scrape_issue_or_collection(self, source: BaseUrlPublisherSource) -> ResultSet | List[Tag] | None:
        self._logger.info(f"Processing Issue / Collection {source.url}")

        try:
            scraper = self._scrape_url(source.url)

            # Find all PDF links using appropriate class or tag (if lambda returns True, it will be included in the list)
            if not (html_tag_list := scraper.find_all(
                "a",
                href=lambda href: href and "/resources/case-studies/" in href,
                class_=lambda class_: class_ and "card-small" in class_ and "ng-star-inserted" in class_,
            )):
                self._save_failure(source.url)

            self._logger.debug(f"HTML links found: {len(html_tag_list)}")
            return html_tag_list
        except Exception as e:
            self._log_and_save_failure(source.url, f"Failed to process Issue / Collection {source.url}. Error: {e}")
            return None

    def _scrape_article(self, source: BaseUrlPublisherSource) -> Tag | None:
        pass
