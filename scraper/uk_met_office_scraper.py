import random
from typing import List, Type
from bs4 import ResultSet, Tag
from selenium.common import TimeoutException

from model.base_url_publisher_models import BaseUrlPublisherSource, BaseUrlPublisherConfig
from scraper.base_url_publisher_scraper import BaseUrlPublisherScraper


class UKMetOfficeScraper(BaseUrlPublisherScraper):
    @property
    def config_model_type(self) -> Type[BaseUrlPublisherConfig]:
        return BaseUrlPublisherConfig

    def _scrape_journal(self, source: BaseUrlPublisherSource) -> ResultSet | List[Tag] | None:
        pass

    def _scrape_issue_or_collection(self, source: BaseUrlPublisherSource) -> List[Tag] | None:
        self._logger.info(f"Processing Issue / Collection {source.url}")

        try:
            self._scrape_url(source.url)

            pdf_tag_list = []

            page_buttons = self._driver.cdp.find_elements("a.role-button.page-link", timeout=0.5)
            # keep only those buttons having a number as a text, and not repeating the same number
            page_buttons = {page_button.text: page_button for page_button in page_buttons if page_button.text.isdigit()}

            for page_button in page_buttons.values():
                self._driver.execute_script("arguments[0].click();", page_button)
                try:
                    self._driver.cdp.assert_element_not_visible("#loading-overflow", timeout=10)
                except TimeoutException:
                    pass

                scraper = self._get_parsed_page_source()
                pdf_tag_list.extend(scraper.find_all("a", href=True, class_="card-link-value"))

                self._driver.cdp.sleep(random.uniform(2, 5))

            self._logger.debug(f"PDF links found: {len(pdf_tag_list)}")

            if not pdf_tag_list:
                self._save_failure(source.url)
            return pdf_tag_list
        except Exception as e:
            self._log_and_save_failure(source.url, f"Failed to process Issue / Collection {source.url}. Error: {e}")
            return None

    def _scrape_article(self, source: BaseUrlPublisherSource) -> Tag | None:
        pass
