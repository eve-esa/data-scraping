from abc import ABC, abstractmethod
import os
import random
from typing import List, Type, Any, Dict, Tuple
from bs4 import BeautifulSoup
from selenium.webdriver import Remote, ChromeOptions
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.chromium.remote_connection import ChromiumRemoteConnection
from selenium.webdriver.remote.client_config import ClientConfig
import time

from helper.constants import OUTPUT_FOLDER
from helper.logger import setup_logger
from model.base_models import BaseConfig
from service.storage import S3Storage


class BaseScraper(ABC):
    def __init__(self) -> None:
        self._logger = setup_logger(self.__class__.__name__)
        self._config_model = None
        self._download_folder_path = None

        self._s3_client = S3Storage()

    def __call__(self, config_model: BaseConfig):
        name_scraper = self.__class__.__name__
        path_file_results = os.path.join(OUTPUT_FOLDER, f"{name_scraper}.json")
        if os.path.exists(path_file_results):
            self._logger.warning(f"Scraper {name_scraper} already done")
            return

        self._logger.info(f"Running scraper {self.__class__.__name__}")
        self._config_model = config_model

        scraping_results = self.scrape(config_model)

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

    def _scrape_url(self, url: str, pause_time: int = 2) -> Tuple[BeautifulSoup, Remote]:
        """
        Scrape the URL using Selenium and BeautifulSoup.

        Args:
            url (str): url contains volume and issue number. Eg: https://www.mdpi.com/2072-4292/1/3
            pause_time (int): time to pause between scrolls

        Returns:
            Tuple[BeautifulSoup, Remote]: A tuple containing the BeautifulSoup object and the WebDriver instance.
        """
        from helper.utils import get_webdriver_config, get_parsed_page_source

        chrome_options = ChromeOptions()
        if self._download_folder_path:
            os.makedirs(self._download_folder_path, exist_ok=True)

            chrome_options.add_experimental_option("prefs", {
                "download.default_directory": self._download_folder_path,
                "download.prompt_for_download": False,
                "download.directory_upgrade": True,
                "safebrowsing.enabled": True
            })

        remote_url, remote_user, remote_password = get_webdriver_config()

        # Create a client config
        client_config = ClientConfig(
            remote_url, keep_alive=True, username=remote_user, password=remote_password
        )

        # Create WebDriver instance
        sbr_connection = ChromiumRemoteConnection(
            remote_url, "goog", "chrome", client_config=client_config
        )

        driver = Remote(sbr_connection, options=chrome_options)

        driver.get(url)
        self._wait_for_page_load(driver)

        # Scroll through the page to load all articles
        last_height = driver.execute_script("return document.body.scrollHeight")

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
            driver.execute_script(f"""
                {scrollable_js}
                if (scrollable) {{
                    scrollable.scrollTop = scrollable.scrollHeight;
                }} else {{
                    window.scrollTo(0, document.body.scrollHeight);
                }}
            """)

            if self._config_model.read_more_button:
                driver.execute_script(f"""
                    const button = Array.from(document.querySelectorAll('{self._config_model.read_more_button.selector}')).find(btn => 
                      btn.textContent.trim().toUpperCase() === "{self._config_model.read_more_button.text}".toUpperCase()
                    );
                    if (button) {{
                      button.click();
                    }}
                """)

            time.sleep(pause_time)

            # Calculate new scroll height and compare with the last height
            new_height = driver.execute_script(f"""
                {scrollable_js}
                return scrollable ? scrollable.scrollHeight : document.body.scrollHeight;
            """)
            if new_height == last_height:
                break
            last_height = new_height

        # Sleep for some time to avoid being blocked by the server on the next request
        time.sleep(random.uniform(0.5, 3.5))

        # Get the fully rendered HTML
        return get_parsed_page_source(driver), driver

    def _wait_for_page_load(self, driver: Remote):
        WebDriverWait(driver, 20).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )

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
