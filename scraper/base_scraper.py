import undetected_chromedriver as uc
import random
from typing import List, Type, Any
from bs4 import BeautifulSoup
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from abc import ABC, abstractmethod
import time
import logging

from constants import OUTPUT_FOLDER, USER_AGENT_LIST, ROTATE_USER_AGENT_EVERY, SECONDS_TO_SLEEP
from model.base_models import BaseConfigScraper
from storage import S3Storage


class BaseScraper(ABC):
    def __init__(self) -> None:
        chrome_options = uc.ChromeOptions()

        # Basic configuration
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument(f"user-agent={random.choice(USER_AGENT_LIST)}")
        chrome_options.add_argument("--headless")  # Run in headless mode (no browser UI)

        # Performance options
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")

        # Cookies and security
        chrome_options.add_argument("--enable-cookies")
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--ignore-certificate-errors")

        # Create WebDriver instance
        self._driver = uc.Chrome(options=chrome_options)

        self._logger = logging.getLogger(self.__class__.__name__)
        self._cookie_handled = False
        self._num_requests = 0
        self._config_model = None

        self._s3_client = S3Storage()

    def __call__(self, config_model: BaseConfigScraper):
        self._logger.info(f"Running scraper {self.__class__.__name__}")
        self._config_model = config_model

        scraping_results = self.scrape(config_model)
        self._driver.quit()

        if scraping_results is None:
            return

        links = self.post_process(scraping_results)
        all_done = self._upload_to_s3(links)

        if all_done:
            from utils import write_json_file, is_json_serializable

            write_json_file(
                f"{OUTPUT_FOLDER}/{self.__class__.__name__}.json",
                scraping_results if is_json_serializable(scraping_results) else links,
            )

        self._logger.info(f"Scraper {self.__class__.__name__} successfully completed.")

    def _scrape_url_by_selenium(self, url: str, pause_time: int = 2) -> str:
        """
        Scrape the URL using Selenium.

        Args:
            url (str): url contains volume and issue number. Eg: https://www.mdpi.com/2072-4292/1/3
            pause_time (int): time to pause between scrolls

        Returns:
            str: the fully rendered HTML of the URL.
        """
        self._driver.get("about:blank")

        self._num_requests += 1
        if self._num_requests % ROTATE_USER_AGENT_EVERY == 0:
            self._driver.execute_cdp_cmd("Network.setUserAgentOverride", {
                "userAgent": random.choice(USER_AGENT_LIST)
            })

        self._driver.get(url)
        # Wait for initial page load
        WebDriverWait(self._driver, 20).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )

        # Handle cookie popup only once, for the first request
        if not self._cookie_handled and self.cookie_selector:
            try:
                cookie_button = WebDriverWait(self._driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, self.cookie_selector))
                )
                self._driver.execute_script("arguments[0].click();", cookie_button)
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
            new_height = self._driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

        # Sleep for some time to avoid being blocked by the server on the next request
        time.sleep(SECONDS_TO_SLEEP)

        # Get the fully rendered HTML
        return self._driver.page_source

    def _scrape_url_by_bs4(self, url: str, pause_time: int = 2) -> BeautifulSoup:
        """
        Scrape the URL using BeautifulSoup.

        Args:
            url (str): url contains volume and issue number. Eg: https://www.mdpi.com/2072-4292/1/3
            pause_time (int): time to pause between scrolls

        Returns:
            BeautifulSoup: the fully rendered HTML of the URL.
        """
        html = self._scrape_url_by_selenium(url, pause_time)
        return BeautifulSoup(html, "html.parser")

    def _upload_to_s3(self, sources_links: List[str]) -> bool:
        """
        Upload the source files to S3.

        Args:
            sources_links (List[str]): The list of links of the various sources.

        Returns:
            bool: True if the upload was successful, False otherwise.
        """
        self._logger.info("Uploading files to S3")

        all_done = True
        for link in sources_links:
            result = self._s3_client.upload(self._config_model.bucket_key, link, self.file_extension)
            if not result:
                all_done = False

            # Sleep after each successful download to avoid overwhelming the server
            time.sleep(random.uniform(2, 5))  # random between 2 and 5 seconds

        return all_done

    @property
    def cookie_selector(self) -> str:
        """
        Return the CSS selector for the cookie popup. This property must be implemented in the derived class.

        Returns:
            str: The CSS selector for the cookie popup.
        """
        return self._config_model.cookie_selector

    @property
    def base_url(self) -> str:
        """
        Return the base URL of the publisher. This property must be implemented in the derived class.

        Returns:
            str: The base URL of the publisher
        """
        return self._config_model.base_url

    @property
    def file_extension(self) -> str:
        """
        Return the file extension of the source files. This property must be implemented in the derived class.

        Returns:
            str: The file extension of the source files
        """
        return self._config_model.file_extension

    @abstractmethod
    def scrape(self, model: BaseConfigScraper) -> Any | None:
        """
        Scrape the resources links. This method must be implemented in the derived class.

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
        retrieve the final list of processed URLs. This method must be implemented in the derived class.

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
        Return the configuration model type. This property must be implemented in the derived class.

        Returns:
            Type[BaseConfigScraper]: The configuration model type
        """
        pass
