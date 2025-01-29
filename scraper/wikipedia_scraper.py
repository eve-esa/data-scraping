from typing import List
from bs4 import ResultSet, Tag
from selenium.webdriver.common.by import By

from model.base_url_publisher_models import BaseUrlPublisherSource
from scraper.base_url_publisher_scraper import BaseUrlPublisherScraper


class WikipediaScraper(BaseUrlPublisherScraper):
    def _scrape_journal(self, source: BaseUrlPublisherSource) -> ResultSet | List[Tag] | None:
        pass

    def _scrape_issue_or_collection(self, source: BaseUrlPublisherSource) -> List[Tag] | None:
        self._logger.info(f"Processing Issue / Collection {source.url}")

        try:
            self._scrape_url(source.url)

            html_tag_list = self._driver.find_elements(value="div.mw-category-generated a", by=By.CSS_SELECTOR)

            self._logger.debug(f"HTML links found: {len(html_tag_list)}")
            return [Tag(name="a", attrs={"href": tag.get_attribute("href")}) for tag in html_tag_list]
        except Exception as e:
            self._logger.error(f"Failed to process Issue / Collection {source.url}. Error: {e}")
            return None

    def _scrape_article(self, source: BaseUrlPublisherSource) -> Tag | None:
        pass
