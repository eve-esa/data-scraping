import os
from typing import Type, Dict

from model.base_mapped_models import BaseMappedCrawlingConfig
from scraper.base_crawling_scraper import BaseCrawlingScraper
from scraper.base_mapped_publisher_scraper import BaseMappedPublisherScraper
from scraper.base_scraper import BaseMappedScraper


class EUMETSATScraper(BaseMappedPublisherScraper):
    @property
    def mapping(self) -> Dict[str, Type[BaseMappedScraper]]:
        return {
            "EUMETSATCrawlingScraper": EUMETSATCrawlingScraper,
        }


class EUMETSATCrawlingScraper(BaseCrawlingScraper, BaseMappedScraper):
    @property
    def config_model_type(self) -> Type[BaseMappedCrawlingConfig]:
        return BaseMappedCrawlingConfig

    @property
    def crawling_folder_path(self) -> str:
        return os.path.join(os.getcwd(), "crawled", "eumetsat")
