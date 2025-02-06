from typing import List, Type, Dict
from bs4 import Tag, ResultSet
from selenium.webdriver.support.wait import WebDriverWait
from seleniumbase import Driver

from model.base_mapped_models import BaseMappedUrlSource, BaseMappedUrlConfig
from scraper.base_mapped_publisher_scraper import BaseMappedPublisherScraper
from scraper.base_scraper import BaseMappedScraper
from scraper.base_url_publisher_scraper import BaseUrlPublisherScraper


class ESAScraper(BaseMappedPublisherScraper):
    @property
    def mapping(self) -> Dict[str, Type[BaseMappedScraper]]:
        return {"EsaUrlScraper": ESAUrlScraper}


class ESAUrlScraper(BaseUrlPublisherScraper, BaseMappedScraper):
    @property
    def config_model_type(self) -> Type[BaseMappedUrlConfig]:
        """
        Return the configuration model type.

        Returns:
            Type[BaseMappedUrlConfig]: The configuration model type
        """
        return BaseMappedUrlConfig

    def _scrape_journal(self, source: BaseMappedUrlSource) -> ResultSet | List[Tag] | None:
        pass

    def _scrape_issue_or_collection(self, source: BaseMappedUrlSource) -> ResultSet | List[Tag] | None:
        self._logger.info(f"Processing Issue / Collection {source.url}")

        try:
            scraper, driver = self._scrape_url(source.url)
            driver.quit()

            href_fnc = lambda href: href and source.href in href and "##" not in href

            # Find all PDF links using appropriate class or tag (if lambda returns True, it will be included in the list)
            if source.class_:
                pdf_tag_list = scraper.find_all("a", href=href_fnc, class_=source.class_)
            else:
                pdf_tag_list = scraper.find_all("a", href=href_fnc)
            self._logger.debug(f"PDF links found: {len(pdf_tag_list)}")

            if not pdf_tag_list:
                self._save_failure(source.url)
            return pdf_tag_list
        except Exception as e:
            self._log_and_save_failure(source.url, f"Failed to process Issue / Collection {source.url}. Error: {e}")
            return None

    def _scrape_article(self, source: BaseMappedUrlSource) -> Tag | None:
        pass

    def _wait_for_page_load(self, driver: Driver, timeout: int | None = 20):
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
                      and not d.execute_script("return document.querySelector('div.v-progress-linear.v-progress-linear--visible')")
        )
