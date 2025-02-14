from typing import List, Type
from bs4 import ResultSet, Tag
from selenium.webdriver.common.by import By

from model.base_url_publisher_models import BaseUrlPublisherSource, BaseUrlPublisherConfig
from scraper.base_url_publisher_scraper import BaseUrlPublisherScraper


class WikipediaScraper(BaseUrlPublisherScraper):
    @property
    def config_model_type(self) -> Type[BaseUrlPublisherConfig]:
        """
        Return the configuration model type.

        Returns:
            Type[BaseUrlPublisherConfig]: The configuration model type
        """
        return BaseUrlPublisherConfig

    def _scrape_journal(self, source: BaseUrlPublisherSource) -> ResultSet | List[Tag] | None:
        pass

    def _scrape_issue_or_collection(self, source: BaseUrlPublisherSource) -> List[Tag] | None:
        self._logger.info(f"Processing Issue / Collection {source.url}")

        driver = None
        try:
            _, driver = self._scrape_url(source.url)

            html_tag_list = driver.find_elements(value="div.mw-category-generated a", by=By.CSS_SELECTOR)

            if not (result := [
                Tag(name="a", attrs={"href": tag.get_attribute("href")})
                for tag in html_tag_list
                if tag.get_attribute("href")
            ]):
                self._save_failure(source.url)

            driver.quit()

            self._logger.debug(f"HTML links found: {len(result)}")
            return result
        except Exception as e:
            if driver:
                driver.quit()

            self._log_and_save_failure(source.url, f"Failed to process Issue / Collection {source.url}. Error: {e}")
            return None

    def _scrape_article(self, source: BaseUrlPublisherSource) -> Tag | None:
        pass
