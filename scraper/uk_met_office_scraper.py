from typing import List
from bs4 import ResultSet, Tag
from selenium.common import TimeoutException
from selenium.webdriver import Remote
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By

from helper.utils import get_parsed_page_source
from model.base_url_publisher_models import BaseUrlPublisherSource
from scraper.base_url_publisher_scraper import BaseUrlPublisherScraper


class UKMetOfficeScraper(BaseUrlPublisherScraper):
    def _scrape_journal(self, source: BaseUrlPublisherSource) -> ResultSet | List[Tag] | None:
        pass

    def _scrape_issue_or_collection(self, source: BaseUrlPublisherSource) -> List[Tag] | None:
        self._logger.info(f"Processing Issue / Collection {source.url}")

        try:
            _, driver = self._scrape_url(source.url)

            pdf_tag_list = []

            page_buttons = driver.find_elements(By.CSS_SELECTOR, "a.role-button.page-link")
            for page_button in page_buttons:
                page_button.click()
                self.__wait_for_loader_hidden(driver)

                scraper = get_parsed_page_source(driver)
                pdf_tag_list.extend(scraper.find_all("a", href=True, class_="card-link-value"))

            driver.quit()
            self._logger.debug(f"PDF links found: {len(pdf_tag_list)}")
            return pdf_tag_list
        except Exception as e:
            self._logger.error(f"Failed to process Issue / Collection {source.url}. Error: {e}")
            return None

    def _scrape_article(self, source: BaseUrlPublisherSource) -> Tag | None:
        pass

    def __wait_for_loader_hidden(self, driver: Remote, timeout: int | None = 10) -> bool:
        """
        Using driver, wait until the parent of the parent of div.loader-admin has style display: none

        Args:
            driver (Remote): The Selenium WebDriver
            timeout (int | None): The maximum time to wait for the loader to be hidden

        Returns:
            bool: True if the loader is hidden, False otherwise
        """

        try:
            loader = driver.find_element(By.ID, "loading-overflow")

            WebDriverWait(driver, timeout).until(
                lambda x: "display: none" in loader.get_attribute("style")
            )
            return True
        except TimeoutException:
            return False
