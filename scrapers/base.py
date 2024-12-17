from typing import List, Type, Any
from bs4 import BeautifulSoup
from pydantic import BaseModel
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.wait import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from abc import ABC, abstractmethod
import time
import logging

from storage import S3Storage

logging.basicConfig(level=logging.INFO)


class BaseModelScraper(BaseModel):
    issue_url: str  # url contains volume and issue number. Eg: https://www.mdpi.com/2072-4292/1/3


class BaseScraper(ABC):
    _output_file = "configs/scraper_config.yaml"

    def __init__(self) -> None:
        chrome_options = Options()
        chrome_options.add_argument(
            "--headless"
        )  # Run in headless mode (no browser UI)
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")

        # Create a new Chrome browser instance
        self._driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()), options=chrome_options
        )
        # driver = webdriver.Chrome(service=Service())

        self._logger = logging.getLogger(__name__)
        self._cookie_handled = False

        self._s3_client = S3Storage()

    def __call__(self, model: BaseModelScraper) -> List:
        scraper = self.__setup_scraper(model.issue_url)
        links = self.scrape(model, scraper)

        # TODO: save links in external file
        # self._save_scraped_list(links)

        self.upload_to_s3(links)

        return self.post_process(links)

    def __scroll_page(self, pause_time: int = 2):
        last_height = self._driver.execute_script("return document.body.scrollHeight")

        while True:
            # Scroll down to the bottom
            self._driver.execute_script(
                "window.scrollTo(0, document.body.scrollHeight);"
            )
            time.sleep(pause_time)

            # Calculate new scroll height and compare with the last height
            new_height = self._driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

    def __handle_cookie_popup(self):
        """
        Handle the cookie popup by interacting with the 'Accept All' button using JavaScript.
        """
        try:
            # Wait for the page to fully load
            WebDriverWait(self._driver, 15).until(lambda d: d.execute_script("return document.readyState") == "complete")
            self._logger.info("Page fully loaded. Attempting to locate the 'Accept All' button using JavaScript.")

            # Execute JavaScript to find and click the "Accept All" button
            self._driver.execute_script("""
                let acceptButton = document.querySelector("body > div.cky-consent-container.cky-classic-bottom > div.cky-consent-bar > div > div > div.cky-notice-btn-wrapper > button.cky-btn.cky-btn-accept");
                if (acceptButton) {
                    acceptButton.click();
                }
            """)
            self._logger.info("'Accept All' button clicked successfully using JavaScript.")
        except Exception as e:
            self._logger.error(f"Failed to handle cookie popup using JavaScript. Error: {e}")

    def __setup_scraper(self, issue_url: str) -> BeautifulSoup:
        """
        Get a URL.

        Args:
            issue_url (str): url contains volume and issue number. Eg:https://www.mdpi.com/2072-4292/1/3

        Returns:
            BeautifulSoup: A BeautifulSoup object containing the fully rendered HTML of the URL.
        """

        self._driver.get(issue_url)
        time.sleep(2)  # Give the page time to load

        # Handle cookie popup only once, for the first request
        if not self._cookie_handled:
            self.__handle_cookie_popup()
            self._cookie_handled = True

        # Scroll through the page to load all articles
        self.__scroll_page()

        # Get the fully rendered HTML and pass it to BeautifulSoup
        html = self._driver.page_source

        return BeautifulSoup(html, "html.parser")

    @abstractmethod
    def scrape(self, model: BaseModelScraper, scraper: BeautifulSoup) -> Any:
        pass

    @abstractmethod
    def post_process(self, links: Any) -> List[str]:
        pass

    @property
    @abstractmethod
    def model_class(self) -> Type[BaseModelScraper]:
        pass

    @abstractmethod
    def upload_to_s3(self, links: Any):
        pass


