import json
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

from constants import config_path
from storage import S3Storage

logging.basicConfig(level=logging.INFO)


class BaseConfigScraper(ABC, BaseModel):
    done: bool = False


class BaseScraper(ABC):
    def __init__(self) -> None:
        chrome_options = Options()

        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--disable-infobars")
        chrome_options.add_argument("--start-maximized")

        chrome_options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        )

        chrome_options.add_argument("--headless")  # Run in headless mode (no browser UI)
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")

        # Create a new Chrome browser instance
        self._driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()), options=chrome_options
        )
        # driver = webdriver.Chrome(service=Service())

        self._driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
            Object.defineProperty(navigator, 'webdriver', {
              get: () => undefined
            })
          """
        })

        self._logger = logging.getLogger(__name__)
        self._cookie_handled = False

        self._s3_client = S3Storage()
        self._done = True

    def __call__(self, model: BaseConfigScraper) -> List[str]:
        self._logger.info(f"Running scraper {self.__class__.__name__}")

        links = self.scrape(model)

        self._driver.quit()

        # TODO: save links in external file
        # self._save_scraped_list(links)

        self.upload_to_s3(links)

        result = self.post_process(links)

        model.done = self._done
        self._update_json_config(self.__class__.__name__)

        self._logger.info(f"Scraper {self.__class__.__name__} successfully completed.")

        return result

    def _update_json_config(self, scraper_name: str):
        """
        Update the JSON file by setting 'done' to True for a given scraper.

        Args:
            scraper_name (str): The name of the scraper to update.
        """

        try:
            with open(config_path, "r") as file:
                config = json.load(file)

            if scraper_name not in config:
                self._logger.error(f"Scraper {scraper_name} not found in the configuration file.")
                return

            config[scraper_name]["done"] = self._done

            with open(config_path, "w") as file:
                json.dump(config, file, indent=4)

            self._logger.info(f"Configuration for {scraper_name} successfully updated.")
        except FileNotFoundError:
            self._logger.error(f"Error: File {config_path} not found.")
        except json.JSONDecodeError:
            self._logger.error(f"Error: the file {config_path} is not a valid JSON.")
        except Exception as e:
            self._logger.error(f"An error occurred while updating the configuration: {e}")

    def _scroll_page(self, pause_time: int = 2):
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

    def _handle_cookie_popup(self):
        """
        Handle the cookie popup by interacting with the 'Accept All' button using JavaScript.
        """
        try:
            # Wait for the page to fully load
            WebDriverWait(self._driver, 15).until(lambda d: d.execute_script("return document.readyState") == "complete")
            self._logger.info("Page fully loaded. Attempting to locate the 'Accept All' button using JavaScript.")

            # Execute JavaScript to find and click the "Accept All" button
            self._driver.execute_script(f"""
                let acceptButton = document.querySelector("{self.cookie_selector}");
                if (acceptButton) {{
                    acceptButton.click();
                }}
            """)
            self._logger.info("'Accept All' button clicked successfully using JavaScript.")
        except Exception as e:
            self._logger.error(f"Failed to handle cookie popup using JavaScript. Error: {e}")

    def _setup_scraper(self, issue_url: str) -> BeautifulSoup:
        """
        Get a URL.

        Args:
            issue_url (str): url contains volume and issue number. Eg:https://www.mdpi.com/2072-4292/1/3

        Returns:
            BeautifulSoup: A BeautifulSoup object containing the fully rendered HTML of the URL.
        """

        self._driver.get(issue_url)
        time.sleep(5)  # Give the page time to load

        # Handle cookie popup only once, for the first request
        if not self._cookie_handled and self.cookie_selector:
            self._handle_cookie_popup()
            self._cookie_handled = True

        # Scroll through the page to load all articles
        self._scroll_page()

        # Get the fully rendered HTML and pass it to BeautifulSoup
        html = self._driver.page_source

        return BeautifulSoup(html, "html.parser")

    @abstractmethod
    def scrape(self, model: BaseConfigScraper) -> Any:
        pass

    @abstractmethod
    def post_process(self, links: Any) -> List[str]:
        pass

    @property
    @abstractmethod
    def model_class(self) -> Type[BaseConfigScraper]:
        pass

    @property
    @abstractmethod
    def cookie_selector(self) -> str:
        pass

    @abstractmethod
    def upload_to_s3(self, links: Any):
        pass
