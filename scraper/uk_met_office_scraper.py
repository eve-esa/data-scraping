import time
from typing import List, Type
from bs4 import ResultSet, Tag
from selenium.common import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from seleniumbase import Driver

from model.base_url_publisher_models import BaseUrlPublisherSource, BaseUrlPublisherConfig
from scraper.base_url_publisher_scraper import BaseUrlPublisherScraper


class UKMetOfficeScraper(BaseUrlPublisherScraper):
    @property
    def config_model_type(self) -> Type[BaseUrlPublisherConfig]:
        """
        Return the configuration model type.

        Returns:
            Type[BaseUrlPublisherConfig]: The configuration model type
        """
        return BaseUrlPublisherConfig

    def setup_driver(self):
        from helper.utils import get_user_agent, headless

        self._driver = Driver(
            browser="chrome",
            undetectable=True,
            locale_code="en",
            headless2=headless(),
            disable_cookies=False,
            window_size="1920,1080",
            window_position="0,0",
            agent=get_user_agent(),
            use_auto_ext=True,
        )

    def _scrape_journal(self, source: BaseUrlPublisherSource) -> ResultSet | List[Tag] | None:
        pass

    def _scrape_issue_or_collection(self, source: BaseUrlPublisherSource) -> List[Tag] | None:
        self._logger.info(f"Processing Issue / Collection {source.url}")

        try:
            self._scrape_url(source.url)

            pdf_tag_list = []

            page_buttons = self._driver.find_elements(value="a.role-button.page-link", by=By.CSS_SELECTOR)
            # keep only those buttons having a number as a text, and not repeating the same number
            page_buttons = {page_button.text: page_button for page_button in page_buttons if page_button.text.isdigit()}

            for page_button in page_buttons.values():
                self._driver.execute_script("arguments[0].click();", page_button)
                try:
                    loader = self._driver.find_element(By.ID, "loading-overflow")

                    WebDriverWait(self._driver, 10).until(
                        lambda x: "display: none" in loader.get_attribute("style")
                    )
                except TimeoutException:
                    pass

                scraper = self._get_parsed_page_source()
                pdf_tag_list.extend(scraper.find_all("a", href=True, class_="card-link-value"))

                time.sleep(1)

            self._logger.debug(f"PDF links found: {len(pdf_tag_list)}")

            if not pdf_tag_list:
                self._save_failure(source.url)
            return pdf_tag_list
        except Exception as e:
            self._log_and_save_failure(source.url, f"Failed to process Issue / Collection {source.url}. Error: {e}")
            return None

    def _scrape_article(self, source: BaseUrlPublisherSource) -> Tag | None:
        pass
