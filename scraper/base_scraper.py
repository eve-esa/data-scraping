import random
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

from constants import OUTPUT_FOLDER, AGENT_LIST
from storage import S3Storage


class BaseConfigScraper(ABC, BaseModel):
    bucket_key: str


class BaseScraper(ABC):
    def __init__(self) -> None:
        chrome_options = Options()

        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--disable-infobars")
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)

        chrome_options.add_argument(
            f"user-agent={random.choice(AGENT_LIST)}"  # Randomly select a user agent from the list
        )

        chrome_options.add_argument(
            "--headless"
        )  # Run in headless mode (no browser UI)
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-popup-blocking")
        chrome_options.add_argument("--disable-notifications")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-background-networking")
        chrome_options.add_argument("--ignore-certificate-errors")

        # Create a new Chrome browser instance
        self._driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()), options=chrome_options
        )
        # driver = webdriver.Chrome(service=Service())

        self._driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {
                "source": """
            Object.defineProperty(navigator, 'webdriver', {
              get: () => undefined
            })
          """
            },
        )

        self._logger = logging.getLogger(self.__class__.__name__)
        self._cookie_handled = False

        self._s3_client = S3Storage()

    def __call__(self, config_model: BaseConfigScraper):
        self._logger.info(f"Running scraper {self.__class__.__name__}")

        scraping_results = self.scrape(config_model)
        self._driver.quit()

        if scraping_results is None:
            return

        links = self.post_process(scraping_results)
        all_done = self._upload_to_s3(links, config_model)

        if all_done:
            from utils import write_json_file

            write_json_file(
                f"{OUTPUT_FOLDER}/{self.__class__.__name__}.json",
                (
                    scraping_results
                    if isinstance(scraping_results, list)
                    or isinstance(scraping_results, dict)
                    else links
                ),
            )

        self._logger.info(f"Scraper {self.__class__.__name__} successfully completed.")

    def _scrape_url(self, url: str, pause_time: int = 2) -> BeautifulSoup:
        """
        Get a URL.

        Args:
            url (str): url contains volume and issue number. Eg:https://www.mdpi.com/2072-4292/1/3

        Returns:
            BeautifulSoup: A BeautifulSoup object containing the fully rendered HTML of the URL.
        """

        self._driver.get(url)
        time.sleep(5)  # Give the page time to load

        # Handle cookie popup only once, for the first request
        if not self._cookie_handled and self.cookie_selector:
            # Handle the cookie popup by interacting with the 'Accept All' button using JavaScript.
            try:
                # Wait for the page to fully load
                WebDriverWait(self._driver, 15).until(
                    lambda d: d.execute_script("return document.readyState")
                    == "complete"
                )
                self._logger.info(
                    "Page fully loaded. Attempting to locate the 'Accept All' button using JavaScript."
                )

                # Execute JavaScript to find and click the "Accept All" button
                self._driver.execute_script(
                    f"""
                            let acceptButton = document.querySelector("{self.cookie_selector}");
                            if (acceptButton) {{
                                acceptButton.click();
                            }}
                        """
                )
                self._logger.info(
                    "'Accept All' button clicked successfully using JavaScript."
                )
                self._cookie_handled = True
            except Exception as e:
                self._logger.error(
                    f"Failed to handle cookie popup using JavaScript. Error: {e}"
                )

        # Scroll through the page to load all articles
        last_height = self._driver.execute_script("return document.body.scrollHeight")

        while True:
            # Scroll down to the bottom
            self._driver.execute_script(
                "window.scrollTo(0, document.body.scrollHeight);"
            )
            time.sleep(pause_time)

            # Calculate new scroll height and compare with the last height
            new_height = self._driver.execute_script(
                "return document.body.scrollHeight"
            )
            if new_height == last_height:
                break
            last_height = new_height

        # Get the fully rendered HTML and pass it to BeautifulSoup
        html = self._driver.page_source

        return BeautifulSoup(html, "html.parser")

    def _upload_to_s3(self, sources_links: List[str], model: BaseConfigScraper) -> bool:
        """
        Upload the source files to S3.

        Args:
            sources_links (List[str]): The list of links of the various sources.
            model (BaseUrlPublisherConfig): The configuration model.

        Returns:
            bool: True if the upload was successful, False otherwise.
        """
        self._logger.info("Uploading files to S3")

        all_done = True
        for link in sources_links:
            result = self._s3_client.upload(model.bucket_key, link)
            if not result:
                all_done = False

            # Sleep after each successful download to avoid overwhelming the server
            time.sleep(random.uniform(2, 5))  # random between 2 and 5 seconds

        return all_done

    @abstractmethod
    def scrape(self, model: BaseConfigScraper) -> Any | None:
        """
        Scrape the resources links.

        Args:
            model (BaseConfigScraper): The configuration model.

        Returns:
            Any: The output of the scraping, or None if something went wrong.
        """
        pass

    @abstractmethod
    def post_process(self, scrape_output: Any) -> List[str]:
        """
        Post-process the scraped output. This method is called after the sources have been scraped. It is used to
        retrieve the final list of processed URLs

        Args:
            scrape_output (Any): The scraped output

        Returns:
            List[str]: A list of processed links
        """
        pass

    @property
    @abstractmethod
    def config_model_type(self) -> Type[BaseConfigScraper]:
        """
        Return the configuration model type. This method must be implemented in the derived class.

        Returns:
            Type[BaseConfigScraper]: The configuration model type
        """
        pass

    @property
    @abstractmethod
    def cookie_selector(self) -> str:
        """
        Return the CSS selector for the cookie popup. This method must be implemented in the derived class.

        Returns:
            str: The CSS selector for the cookie popup.
        """
        pass

    @property
    @abstractmethod
    def base_url(self) -> str:
        """
        Return the base URL of the publisher.

        Returns:
            str: The base URL of the publisher
        """
        pass
