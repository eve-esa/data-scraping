from abc import ABC, abstractmethod
import os
import random
from typing import List, Type, Any, Dict
from bs4 import BeautifulSoup
from selenium.common import TimeoutException
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from seleniumbase import Driver
from seleniumbase.fixtures import constants
import time

from helper.constants import OUTPUT_FOLDER
from helper.logger import setup_logger
from model.base_models import BaseConfig
from service.storage import S3Storage


class BaseScraper(ABC):
    def __init__(self) -> None:
        self._driver: Driver = None

        self._logger = setup_logger(self.__class__.__name__)
        self._cookie_handled = False
        self._config_model = None
        self._download_folder_path = constants.Files.DOWNLOADS_FOLDER

        self._s3_client = S3Storage()

    def __call__(self, config_model: BaseConfig):
        name_scraper = self.__class__.__name__
        path_file_results = os.path.join(OUTPUT_FOLDER, f"{name_scraper}.json")
        if os.path.exists(path_file_results):
            self._logger.warning(f"Scraper {name_scraper} already done")
            return

        self._logger.info(f"Running scraper {self.__class__.__name__}")
        self.set_config_model(config_model)

        self.setup_driver()
        scraping_results = self.scrape()
        self.shutdown_driver()

        if scraping_results is None:
            return

        links = self.post_process(scraping_results)
        all_done = self.upload_to_s3(links)

        if all_done:
            from helper.utils import write_json_file, is_json_serializable
            write_json_file(path_file_results, scraping_results if is_json_serializable(scraping_results) else links)

            self._logger.info(f"Scraper {self.__class__.__name__} successfully completed.")
            return

        self._logger.warning(f"Something went wrong with Scraper {self.__class__.__name__}: unsuccessfully completed.")

    def set_config_model(self, config_model: BaseConfig):
        self._config_model = config_model
        return self

    def setup_driver(self):
        from helper.utils import get_user_agent, get_static_proxy_config

        self._driver = Driver(
            browser="chrome",
            uc=True,
            locale_code="en",
            headless=self._config_model.headless,
            headless1=self._config_model.headless,
            headless2=self._config_model.headless,
            proxy=get_static_proxy_config(),
            disable_cookies=False,
            disable_gpu=True,
            no_sandbox=True,
            window_size="1920,1080",
            window_position="0,0",
            agent=get_user_agent(),
            disable_ws=True,
            devtools=True,
        )

    def shutdown_driver(self):
        self._driver.quit()

    def _scrape_url(self, url: str, cookie_wait: int = 3, pause_time: int = 2) -> BeautifulSoup:
        """
        Scrape the URL using Selenium and BeautifulSoup.

        Args:
            url (str): url contains volume and issue number. Eg: https://www.mdpi.com/2072-4292/1/3
            cookie_wait (int): time to wait for the cookie popup to appear
            pause_time (int): time to pause between scrolls

        Returns:
            BeautifulSoup: the fully rendered HTML of the URL.
        """

        self._driver.get(url.replace('"', '\\\"'))
        self._wait_for_page_load()

        # Handle cookie popup only once, for the first request
        if not self._cookie_handled and self._config_model.cookie_selector:
            try:
                cookie_button = WebDriverWait(self._driver, cookie_wait).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, self._config_model.cookie_selector))
                )
                self._driver.execute_script("arguments[0].click();", cookie_button)
                self._cookie_handled = True
            except TimeoutException as e:
                self._logger.warning(f"Cookie popup not found. Error: {e}")

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
        time.sleep(random.uniform(0.5, 3.5))

        # Get the fully rendered HTML
        return self._get_parsed_page_source()

    def _wait_for_page_load(self, timeout: int | None = 20):
        WebDriverWait(self._driver, timeout).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )

    def _get_parsed_page_source(self) -> BeautifulSoup:
        """
        Get the page source parsed by BeautifulSoup.

        Returns:
            BeautifulSoup: The parsed page source.
        """
        return BeautifulSoup(self._driver.get_page_source(), "html.parser")

    def upload_to_s3(self, sources_links: Dict[str, List[str]] | List[str], **kwargs) -> bool:
        """
        Upload the source files to S3.

        Args:
            sources_links (Dict[str, List[str]] | List[str]): The list of links of the various sources.

        Returns:
            bool: True if the upload was successful, False otherwise.
        """
        self._logger.debug("Uploading files to S3")

        all_done = True
        for link in sources_links:
            result = self._s3_client.upload(self.bucket_key, link, self.file_extension)
            if not result:
                all_done = False

            # Sleep after each successful download to avoid overwhelming the server
            time.sleep(random.uniform(2, 5))

        return all_done

    @property
    def base_url(self) -> str:
        """
        Return the base URL of the publisher.

        Returns:
            str: The base URL of the publisher
        """
        return self._config_model.base_url

    @property
    def bucket_key(self) -> str:
        """
        Return the bucket key of the publisher.

        Returns:
            str: The bucket key of the publisher
        """
        return self._config_model.bucket_key

    @property
    def file_extension(self) -> str:
        """
        Return the file extension linked to the publisher.

        Returns:
            str: The file extension linked to the publisher
        """
        return self._config_model.file_extension

    @abstractmethod
    def scrape(self) -> Any | None:
        """
        Scrape the resources links. This method must be implemented in the derived class.

        Returns:
            Any: The output of the scraping, or None if something went wrong.
        """
        pass

    @abstractmethod
    def post_process(self, scrape_output: Any) -> Dict[str, List[str]] | List[str]:
        """
        Post-process the scraped output. This method is called after the sources have been scraped. It is used to
        retrieve the final list of processed URLs. This method must be implemented in the derived class.

        Args:
            scrape_output (Any): The scraped output

        Returns:
            Dict[str, List[str]] | List[str]: A dictionary or a list containing the processed links
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
