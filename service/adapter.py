from typing import Any, Type

from helper.utils import get_scraped_url
from model.base_mapped_models import BaseMappedSourceConfig
from scraper.base_scraper import BaseScraper
from scraper.base_url_publisher_scraper import BaseUrlPublisherScraper


class ScrapeAdapter:
    def __init__(self, config_model: BaseMappedSourceConfig, scraper: Type[BaseScraper] | None = None):
        self.__scraper_type = scraper
        self.__config_model = config_model

    def scrape(self) -> Any:
        if self.__scraper_type is None:
            results = self.__config_model.urls
        else:
            scraper = self.__scraper_type()
            scraper._config_model = self.__config_model

            results = scraper.scrape(self.__config_model)

            if results is not None and issubclass(self.__scraper_type, BaseUrlPublisherScraper):
                results = [
                    get_scraped_url(tag, self.__config_model.base_url) for tag in results
                ]

        return results
