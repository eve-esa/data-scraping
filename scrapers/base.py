from typing import List
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.wait import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from abc import ABC, abstractmethod
import time
import logging

logging.basicConfig(level=logging.INFO)


class BaseScraper(ABC):
    _output_file = "configs/scraper_config.yaml"

    def __init__(self) -> None:
        self.driver = self._setup_selenium()

        self.logger = logging.getLogger(__name__)
        self.cookie_handled = False

    def _setup_selenium(self):
        chrome_options = Options()
        chrome_options.add_argument(
            "--headless"
        )  # Run in headless mode (no browser UI)
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")

        # Create a new Chrome browser instance
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()), options=chrome_options
        )
        # driver = webdriver.Chrome(service=Service())
        return driver

    def _scroll_page(self, pause_time: int = 2):
        last_height = self.driver.execute_script("return document.body.scrollHeight")

        while True:
            # Scroll down to the bottom
            self.driver.execute_script(
                "window.scrollTo(0, document.body.scrollHeight);"
            )
            time.sleep(pause_time)

            # Calculate new scroll height and compare with the last height
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

    def _handle_cookie_popup(self):
        """
        Handle the cookie popup by interacting with the 'Accept All' button using JavaScript.
        """
        try:
            # Wait for the page to fully load
            WebDriverWait(self.driver, 15).until(lambda d: d.execute_script("return document.readyState") == "complete")
            self.logger.info("Page fully loaded. Attempting to locate the 'Accept All' button using JavaScript.")

            # Execute JavaScript to find and click the "Accept All" button
            self.driver.execute_script("""
                let acceptButton = document.querySelector("body > div.cky-consent-container.cky-classic-bottom > div.cky-consent-bar > div > div > div.cky-notice-btn-wrapper > button.cky-btn.cky-btn-accept");
                if (acceptButton) {
                    acceptButton.click();
                }
            """)
            self.logger.info("'Accept All' button clicked successfully using JavaScript.")
        except Exception as e:
            self.logger.error(f"Failed to handle cookie popup using JavaScript. Error: {e}")

    def _setup_scraper(self, issue_url: str) -> BeautifulSoup:
        """
        Get a URL.

        Args:
            issue_url (str): url contains volume and issue number. Eg:https://www.mdpi.com/2072-4292/1/3

        Returns:
            BeautifulSoup: A BeautifulSoup object containing the fully rendered HTML of the URL.
        """

        self.driver.get(issue_url)
        time.sleep(2)  # Give the page time to load

        # Handle cookie popup only once, for the first request
        if not self.cookie_handled:
            self._handle_cookie_popup()
            self.cookie_handled = True

        # Scroll through the page to load all articles
        self._scroll_page()

        # Get the fully rendered HTML and pass it to BeautifulSoup
        html = self.driver.page_source

        return BeautifulSoup(html, "html.parser")

    @abstractmethod
    def __call__(self, *args, **kwargs) -> List:
        pass

    @property
    @abstractmethod
    def model_class(self) -> str:
        pass
