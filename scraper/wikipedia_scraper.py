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

        try:
            self._scrape_url(source.url)

            html_tag_list = self._driver.find_elements(By.CSS_SELECTOR, "div.mw-category-generated a")
            result = [
                Tag(name="a", attrs={"href": tag.get_attribute("href")})
                for tag in html_tag_list
                if tag.get_attribute("href")
            ]

            self._logger.debug(f"HTML links found: {len(result)}")
            return result
        except Exception as e:
            self._logger.error(f"Failed to process Issue / Collection {source.url}. Error: {e}")
            return None

    def _scrape_article(self, source: BaseUrlPublisherSource) -> Tag | None:
        pass
