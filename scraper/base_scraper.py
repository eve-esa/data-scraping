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
from torpy.http.requests import tor_requests_session

from constants import OUTPUT_FOLDER, USER_AGENT_LIST, ROTATE_USER_AGENT_EVERY
from storage import S3Storage


class BaseConfigScraper(ABC, BaseModel):
    bucket_key: str


class BaseScraper(ABC):
    def __init__(self) -> None:
        self._logger = logging.getLogger(self.__class__.__name__)
        self._cookie_handled = False
        self._num_requests = 0

        self._driver = None
        if self.scrape_by_selenium:
            self.__init_selenium_driver()

        self._s3_client = S3Storage()

    def __init_selenium_driver(self):
        chrome_options = Options()

        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--disable-infobars")
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)

        chrome_options.add_argument(f"user-agent={random.choice(AGENT_LIST)}")  # Randomly select a user agent
        chrome_options.add_argument("--headless")  # Run in headless mode (no browser UI)
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-popup-blocking")
        chrome_options.add_argument("--disable-notifications")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-background-networking")
        chrome_options.add_argument("--ignore-certificate-errors")
        chrome_options.add_argument("--incognito")
        chrome_options.add_argument("--disable-cache")
        chrome_options.add_argument("--disable-application-cache")
        chrome_options.add_argument("--disable-offline-load-stale-cache")
        chrome_options.add_argument("--disk-cache-size=0")

        self._driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()), options=chrome_options
        )

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

    def __call__(self, config_model: BaseConfigScraper):
        self._logger.info(f"Running scraper {self.__class__.__name__}")

        try:
            scraping_results = self.scrape(config_model)
        finally:
            if self._driver:
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
                    if isinstance(scraping_results, list) or isinstance(scraping_results, dict)
                    else links
                ),
            )

        self._logger.info(f"Scraper {self.__class__.__name__} successfully completed.")

    def _rotate_user_agent(self) -> None:
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
        self._driver.execute_cdp_cmd(
            "Network.enable",
            {}
        )

        self._driver.execute_cdp_cmd(
            "Network.setUserAgentOverride",
            {
                "userAgent": f"{random.choice(USER_AGENT_LIST)}",
            }
        )

    def _scrape_url(self, url: str, pause_time: int = 2) -> BeautifulSoup:
        """
        Scrape the URL and return the BeautifulSoup object. This method is used to scrape the URL and return the fully
        rendered HTML.

        Args:
            url (str): url contains volume and issue number. Eg: https://www.mdpi.com/2072-4292/1/3

        Returns:
            BeautifulSoup: A BeautifulSoup object containing the fully rendered HTML of the URL.
        """
        self._num_requests += 1
        if self._num_requests % ROTATE_USER_AGENT_EVERY == 0:
            self._rotate_user_agent()

        if self.scrape_by_selenium:
            html = self.__scrape_by_selenium(url, pause_time)
        else:
            html = self.__scrape_by_tor(url)

        return BeautifulSoup(html, "html.parser")

    def __scrape_by_tor(self, url: str, pause_time: int = 2) -> str:
        """
        Scrape the URL by Tor Network and return the fully rendered HTML.

        Args:
            url (str): The URL to scrape.
            pause_time (int): The time to pause before scraping the next URL.

        Returns:
            str: The fully rendered HTML of the URL.
        """
        headers = {
            "User-Agent": random.choice(AGENT_LIST),
            "Accept": "application/pdf,*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": self.referer_url,
        }

        with tor_requests_session(headers=headers) as sess:
            response = sess.get(url, timeout=10)
            response.raise_for_status()

        time.sleep(pause_time)

        return response.text

    def __scrape_by_selenium(self, url: str, pause_time: int = 2) -> str:
        """
        Scrape the URL using Selenium. This method is used to scrape the URL and return the fully rendered HTML.

        Args:
            url (str): The URL to scrape.
            pause_time (int): The time to pause between scrolling the page.

        Returns:
            str: The fully rendered HTML of the URL.
        """
        self._driver.get(url)
        time.sleep(5)  # Give the page time to load

        # Handle cookie popup only once, for the first request
        if not self._cookie_handled and self.cookie_selector:
            # Handle the cookie popup by interacting with the 'Accept All' button using JavaScript.
            try:
                # Wait for the page to fully load
                WebDriverWait(self._driver, 15).until(
                    lambda d: d.execute_script("return document.readyState") == "complete"
                )
                self._logger.info("Page fully loaded. Attempting to locate the 'Accept All' button using JavaScript.")

                # Execute JavaScript to find and click the "Accept All" button
                self._driver.execute_script(f"""
                            let acceptButton = document.querySelector("{self.cookie_selector}");
                            if (acceptButton) {{
                                acceptButton.click();
                            }}
                        """)
                self._logger.info("'Accept All' button clicked successfully using JavaScript.")
                self._cookie_handled = True
            except Exception as e:
                self._logger.error(f"Failed to handle cookie popup using JavaScript. Error: {e}")

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

        # Get the fully rendered HTML and pass it to BeautifulSoup
        return self._driver.page_source

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
            result = self._s3_client.upload(
                model.bucket_key,
                link,
                self.file_extension,
                referer_url=self.referer_url,
                with_tor=(not self.scrape_by_selenium)
            )
            if not result:
                all_done = False

            # Sleep after each successful download to avoid overwhelming the server
            time.sleep(random.uniform(2, 5))  # random between 2 and 5 seconds

        return all_done

    @property
    def scrape_by_selenium(self) -> bool:
        return True

    @property
    def referer_url(self) -> str | None:
        return None

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

    @property
    @abstractmethod
    def cookie_selector(self) -> str:
        """
        Return the CSS selector for the cookie popup. This property must be implemented in the derived class.

        Returns:
            str: The CSS selector for the cookie popup.
        """
        pass

    @property
    @abstractmethod
    def base_url(self) -> str:
        """
        Return the base URL of the publisher. This property must be implemented in the derived class.

        Returns:
            str: The base URL of the publisher
        """
        pass

    @property
    @abstractmethod
    def file_extension(self) -> str:
        """
        Return the file extension of the source files. This property must be implemented in the derived class.

        Returns:
            str: The file extension of the source files
        """
        pass
