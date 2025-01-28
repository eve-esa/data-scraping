from typing import Any, Type, List

from model.base_mapped_models import BaseMappedSourceConfig
from scraper.base_scraper import BaseScraper


class ScrapeAdapter:
    def __init__(self, config_model: BaseMappedSourceConfig, scraper: Type[BaseScraper] | None = None):
        self.__scraper_type = scraper
        self.__config_model = config_model

    def scrape(self) -> Any:
        if self.__scraper_type is None:
            return self.__config_model.urls

        scraper = self.__scraper_type()
        scraper._config_model = self.__config_model

        scraper.setup_driver()
        results = scraper.set_config_model(self.__config_model).scrape()
        scraper.shutdown_driver()

        return results

    def post_process(self, scrape_output: Any) -> Any:
        if self.__scraper_type is None:
            return scrape_output

        scraper = self.__scraper_type()
        return scraper.set_config_model(self.__config_model).post_process(scrape_output)

    def upload_to_s3(self, scrape_output: List[str], bucket_key: str, file_extension: str) -> bool:
        from scraper.direct_links_scraper import DirectLinksScraper

        if self.__scraper_type is not None:
            scraper = self.__scraper_type()
            return scraper.set_config_model(self.__config_model).upload_to_s3(scrape_output)

        scraper = DirectLinksScraper()
        return scraper.upload_to_s3(scrape_output, bucket_key=bucket_key, file_extension=file_extension)
