from typing import Any, Type, List, Dict
from seleniumbase import SB

from helper.utils import get_sb_configuration
from model.base_mapped_models import BaseMappedSourceConfig
from model.sql_models import ScraperFailure
from scraper.base_scraper import BaseScraper


class ScrapeAdapter:
    def __init__(
        self, config_model: BaseMappedSourceConfig, logging_scraper: str, scraper: Type[BaseScraper] | None = None
    ):
        self.__scraper_type = scraper
        self.__logging_scraper = logging_scraper
        self.__config_model = config_model

    def scrape(self) -> Any:
        if self.__scraper_type is None:
            return self.__config_model.urls

        scraper = self.__scraper_type()
        scraper.set_config_model(self.__config_model).set_logging_db_scraper(self.__logging_scraper)

        with SB(**get_sb_configuration()) as driver:
            driver.activate_cdp_mode()
            driver.cdp.maximize()
            results = scraper.set_driver(driver).scrape()

        return results

    def scrape_failure(self, failure: ScraperFailure) -> List[str]:
        if self.__scraper_type is None:
            return [failure.source]

        scraper = self.__scraper_type()
        scraper.set_config_model(self.__config_model).set_logging_db_scraper(self.__logging_scraper)
        return scraper.scrape_failure(failure)

    def post_process(self, scrape_output: Any) -> Any:
        if self.__scraper_type is None:
            return scrape_output

        scraper = self.__scraper_type()
        scraper.set_config_model(self.__config_model).set_logging_db_scraper(self.__logging_scraper)
        return scraper.post_process(scrape_output)

    def upload_to_s3(
        self, scrape_output: List[str] | Dict[str, List[str]], bucket_key: str, files_by_request: bool
    ) -> bool:
        from scraper.direct_links_scraper import DirectLinksScraper
        if self.__config_model.bucket_key is None:
            self.__config_model.bucket_key = bucket_key
        if self.__config_model.files_by_request is None:
            self.__config_model.files_by_request = files_by_request

        if self.__scraper_type is not None:
            scraper = self.__scraper_type()
        else:
            scraper = DirectLinksScraper()
        scraper.set_config_model(self.__config_model).set_logging_db_scraper(self.__logging_scraper)
        return scraper.upload_to_s3(scrape_output)
