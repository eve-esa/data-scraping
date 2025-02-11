import json
import os
from abc import ABC, abstractmethod
import random
from typing import List, Type, Any, Dict, Tuple, Final
from bs4 import BeautifulSoup
from selenium.common import TimeoutException
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from seleniumbase import Driver
from seleniumbase.fixtures import constants
import time

from helper.logger import setup_logger
from model.base_models import BaseConfig
from model.sql_models import UploadedResource, ScraperOutput, ScraperFailure
from service.analytics_manager import AnalyticsManager
from service.storage import S3Storage
from repository.scraper_failure_repository import ScraperFailureRepository
from repository.scraper_output_repository import ScraperOutputRepository
from repository.uploaded_resource_repository import UploadedResourceRepository


class BaseScraper(ABC):
    def __init__(self) -> None:
        self._config_model = None
        self._logging_db_scraper = self.__class__.__name__
        self._download_folder_path = constants.Files.DOWNLOADS_FOLDER

        self._logger = setup_logger(self.__class__.__name__)
        self._s3_client = S3Storage()

        self._scraper_failure_repository = ScraperFailureRepository()
        self._scraper_output_repository = ScraperOutputRepository()
        self._uploaded_resource_repository = UploadedResourceRepository()

        self._analytics_manager = AnalyticsManager()

    def __call__(self, config_model: BaseConfig, force: bool = False):
        from helper.utils import is_json_serializable

        name_scraper = self.__class__.__name__
        if not force and self._scraper_output_repository.get_one_by({"scraper": name_scraper}):
            self._logger.warning(f"Scraper {name_scraper} already done")
            return

        self._logger.info(f"Running scraper {self.__class__.__name__}")
        self.set_config_model(config_model)
        self._scraper_failure_repository.delete_by({"scraper": name_scraper})

        scraping_results = self.scrape()
        if scraping_results is None:
            return

        links = self.post_process(scraping_results)
        self.upload_to_s3(links)

        output = ScraperOutput(
            scraper=name_scraper,
            output=json.dumps(scraping_results if is_json_serializable(scraping_results) else links)
        )
        self._scraper_output_repository.upsert(output, {"scraper": output.scraper}, {"output": output.output})

        self._analytics_manager.build_and_store_analytics(name_scraper)

        self._logger.info(f"Scraper {self.__class__.__name__} successfully completed.")
        return

    def set_config_model(self, config_model: BaseConfig):
        self._config_model = config_model
        return self

    def set_logging_db_scraper(self, scraper: str):
        self._logging_db_scraper = scraper
        return self

    def _scrape_url(self, url: str, cookie_wait: int = 3, pause_time: int = 2) -> Tuple[BeautifulSoup, Driver]:
        """
        Scrape the URL using Selenium and BeautifulSoup.

        Args:
            url (str): url contains volume and issue number. Eg: https://www.mdpi.com/2072-4292/1/3
            cookie_wait (int): time to wait for the cookie popup to appear
            pause_time (int): time to pause between scrolls

        Returns:
            BeautifulSoup: the fully rendered HTML of the URL.
        """
        from helper.utils import get_user_agent, get_static_proxy_config, get_parsed_page_source

        driver = Driver(
            browser="chrome",
            undetectable=True,
            uc_cdp_events=True,
            locale_code="en",
            headless=self._config_model.headless,
            headless1=self._config_model.headless,
            headless2=self._config_model.headless,
            proxy=get_static_proxy_config(),
            disable_cookies=False,
            window_size="1920,1080",
            window_position="0,0",
            agent=get_user_agent(),
            devtools=True,
            use_auto_ext=True,
        )

        driver.get(url.replace('"', '\\\"'))
        driver.uc_gui_click_captcha()
        self._wait_for_page_load(driver)

        # Handle cookie popup only once, for the first request
        if self._config_model.cookie_selector:
            try:
                cookie_button = WebDriverWait(driver, cookie_wait).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, self._config_model.cookie_selector))
                )
                driver.execute_script("arguments[0].click();", cookie_button)
            except TimeoutException as e:
                self._logger.warning(f"Cookie popup not found. {e}")

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

    def _wait_for_page_load(self, driver: Driver, timeout: int | None = 20):
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )

    def _save_failure(self, source: str, message: str | None = None):
        message = message or "No source link found."
        self._scraper_failure_repository.insert(
            ScraperFailure(scraper=self._logging_db_scraper, source=source, message=message)
        )

    def _log_and_save_failure(self, url: str, message: str):
        self._logger.error(f"{message} (url {url})")
        self._save_failure(url, message=message)

    def upload_to_s3(self, sources_links: Dict[str, List[str]] | List[str]):
        """
        Upload the source files to S3.

        Args:
            sources_links (Dict[str, List[str]] | List[str]): The list of links of the various sources.
        """
        self._logger.debug("Uploading files to S3")

        for link in sources_links:
            current_resource = self._uploaded_resource_repository.get_by_url(
                self.__class__.__name__,
                self._config_model.bucket_key,
                link,
                self._config_model.file_extension
            )
            if not self._check_valid_resource(current_resource, link):
                continue

            self._upload_resource_to_s3_and_store_to_db(current_resource)

    def _check_valid_resource(self, resource: UploadedResource, resource_name: str) -> bool:
        if resource.id and resource.success:
            self._logger.warning(f"Resource {resource_name} already exists in the database, skipping upload.")
            return False
        if not resource.content:
            self._logger.warning(f"We were unable to retrieve the content from {resource_name}, skipping upload.")
            return False
        return True

    def _upload_resource_to_s3_and_store_to_db(self, resource: UploadedResource) -> bool:
        main_folder: Final[str] = os.getenv("AWS_MAIN_FOLDER", "raw_data")
        resource.bucket_key = resource.bucket_key.format(main_folder=main_folder)

        result = self._s3_client.upload_content(resource)
        resource.success = result
        self._uploaded_resource_repository.upsert(resource, {"sha256": resource.sha256}, keys_to_purge=["content"])

        # Sleep after each successful download to avoid overwhelming the server
        time.sleep(random.uniform(2, 5))

        return result

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
