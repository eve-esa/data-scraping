import os
import undetected_chromedriver as uc
import random
from typing import List, Type, Any
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from abc import ABC, abstractmethod
import time
import logging

from helper.constants import OUTPUT_FOLDER, ROTATE_USER_AGENT_EVERY
from model.base_models import BaseConfig
from service.storage import S3Storage


class BaseScraper(ABC):
    def __init__(self) -> None:
        self._driver = None

        self._logger = logging.getLogger(self.__class__.__name__)
        self._cookie_handled = False
        self._num_requests = 0
        self._config_model = None

        self._s3_client = S3Storage()

    def __call__(self, config_model: BaseConfig):
        self.setup_driver()

        name_scraper = self.__class__.__name__
        path_file_results = os.path.join(OUTPUT_FOLDER, f"{name_scraper}.json")
        if os.path.exists(path_file_results):
            self._logger.warning(f"Scraper {name_scraper} already done")
            return

        self._logger.info(f"Running scraper {self.__class__.__name__}")
        self._config_model = config_model

        scraping_results = self.scrape(config_model)

        self.shutdown_driver()

        if scraping_results is None:
            return

        links = self.post_process(scraping_results)
        all_done = self._upload_to_s3(links)

        if all_done:
            from helper.utils import write_json_file, is_json_serializable
            write_json_file(path_file_results, scraping_results if is_json_serializable(scraping_results) else links)

        self._logger.info(f"Scraper {self.__class__.__name__} successfully completed.")

    def setup_driver(self):
        chrome_options = uc.ChromeOptions()

        # Basic configuration
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument(f"--user-agent={UserAgent().random}")
        chrome_options.add_argument("--headless=new")  # Run in headless mode (no browser UI)

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

    def shutdown_driver(self):
        if self._driver:
            self._driver.quit()

    def _scrape_url(self, url: str, pause_time: int = 2) -> BeautifulSoup:
        """
        Scrape the URL using Selenium and BeautifulSoup.

        Args:
            url (str): url contains volume and issue number. Eg: https://www.mdpi.com/2072-4292/1/3
            pause_time (int): time to pause between scrolls

        Returns:
            BeautifulSoup: the fully rendered HTML of the URL.
        """
        self._driver.get("about:blank")

        self._num_requests += 1
        if self._num_requests % ROTATE_USER_AGENT_EVERY == 0:
            self._driver.execute_cdp_cmd("Network.setUserAgentOverride", {
                "userAgent": UserAgent().random
            })

        self._driver.get(url)
        # Wait for initial page load
        WebDriverWait(self._driver, 20).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )

        # Handle cookie popup only once, for the first request
        if not self._cookie_handled and self._config_model.cookie_selector:
            cookie_button = WebDriverWait(self._driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, self._config_model.cookie_selector))
            )
            self._driver.execute_script("arguments[0].click();", cookie_button)
            self._cookie_handled = True

        # Scroll through the page to load all articles
        last_height = self._driver.execute_script("return document.body.scrollHeight")

        scrollable_js = """
            function getScrollableElement() {
                const elements = document.querySelectorAll('*');
                for (const element of elements) {
                    if (element.scrollHeight > element.clientHeight) {
                        return element;
                    }
                }
                return null;
            }
            const scrollable = getScrollableElement();
        """

        while True:
            # Scroll down to the bottom
            self._driver.execute_script(f"""
                {scrollable_js}
                if (scrollable) {{
                    scrollable.scrollTop = scrollable.scrollHeight;
                }} else {{
                    window.scrollTo(0, document.body.scrollHeight);
                }}
            """)

            if self._config_model.read_more_button:
                self._driver.execute_script(f"""
                    const button = Array.from(document.querySelectorAll('{self._config_model.read_more_button.selector}')).find(btn => 
                      btn.textContent.trim().toUpperCase() === "{self._config_model.read_more_button.text}".toUpperCase()
                    );
                    if (button) {{
                      button.click();
                    }}
                """)

            time.sleep(pause_time)

            # Calculate new scroll height and compare with the last height
            new_height = self._driver.execute_script(f"""
                {scrollable_js}
                return scrollable ? scrollable.scrollHeight : document.body.scrollHeight;
            """)
            if new_height == last_height:
                break
            last_height = new_height

        # Sleep for some time to avoid being blocked by the server on the next request
        time.sleep(random.uniform(1, 5))

        # Get the fully rendered HTML
        return self._get_parsed_page_source()

    def _get_parsed_page_source(self) -> BeautifulSoup:
        """
        Get the page source parsed by BeautifulSoup.

        Returns:
            BeautifulSoup: The parsed page source.
        """
        return BeautifulSoup(self._driver.page_source, "html.parser")

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
            result = self._s3_client.upload(self._config_model.bucket_key, link, self._config_model.file_extension)
            if not result:
                all_done = False

            # Sleep after each successful download to avoid overwhelming the server
            time.sleep(random.uniform(2, 5))

        return all_done

    @property
    def base_url(self) -> str:
        """
        Return the base URL of the publisher. This property must be implemented in the derived class.

        Returns:
            str: The base URL of the publisher
        """
        return self._config_model.base_url

    @abstractmethod
    def scrape(self, model: BaseConfig) -> Any | None:
        """
        Scrape the resources links. This method must be implemented in the derived class.

        Args:
            model (BaseConfig): The configuration model.

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
    def config_model_type(self) -> Type[BaseConfig]:
        """
        Return the configuration model type. This property must be implemented in the derived class.

        Returns:
            Type[BaseConfig]: The configuration model type
        """
        pass


class BaseMappedScraper(ABC):
    pass
