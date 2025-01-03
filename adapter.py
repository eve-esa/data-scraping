from typing import Any, Dict, Type

from model.base_mapped_models import BaseMappedSource, SourceType
from scraper.base_scraper import BaseScraper
from utils import get_scraped_url


class ScrapeAdapter:
    def __init__(self, source: BaseMappedSource, mapping: Dict[str, Type[BaseScraper]]):
        self.__mapping = mapping
        self.__source = source

    def scrape(self) -> Any:
        config_model = self.__source.config

        if self.__source.type == SourceType.DIRECT:
            results = config_model.urls
        else:
            scraper = self.__mapping.get(self.__source.type)()
            scraper._config_model = config_model
            scraper.setup_driver()

            results = scraper.scrape(config_model)

            if self.__source.type == SourceType.URL and results is not None:
                results = [
                    get_scraped_url(tag, config_model.base_url) for tag in results
                ]
            scraper.shutdown_driver()

        return results
