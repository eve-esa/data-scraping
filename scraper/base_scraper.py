import json
import os
from abc import ABC, abstractmethod
import random
from typing import List, Type, Any, Dict, Final
from bs4 import BeautifulSoup
from seleniumbase import SB
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
        self._driver: SB = None
        self._config_model = None
        self._logging_db_scraper = self.__class__.__name__

        self._logger = setup_logger(self.__class__.__name__)
        self._s3_client = S3Storage()

        self._scraper_failure_repository = ScraperFailureRepository()
        self._scraper_output_repository = ScraperOutputRepository()
        self._uploaded_resource_repository = UploadedResourceRepository()

        self._analytics_manager = AnalyticsManager()

    def __call__(self, config_model: BaseConfig, force: bool = False):
        from helper.utils import is_json_serializable

        if not force and self._scraper_output_repository.get_one_by({"scraper": self._logging_db_scraper}):
            self._logger.warning(f"Scraper {self.__class__.__name__} already done")
            return

        self._logger.info(f"Running scraper {self.__class__.__name__}")
        self.set_config_model(config_model)
        self._scraper_failure_repository.delete_by({"scraper": self._logging_db_scraper})

        if (scraping_results := self._run_scraping()) is None:
            return

        links = self.post_process(scraping_results)
        self.upload_to_s3(links)

        output = ScraperOutput(
            scraper=self._logging_db_scraper,
            output=json.dumps(scraping_results if is_json_serializable(scraping_results) else links)
        )
        self._scraper_output_repository.upsert(output, {"scraper": output.scraper}, {"output": output.output})

        self._analytics_manager.build_and_store_analytics(self._logging_db_scraper)

        self._logger.info(f"Scraper {self.__class__.__name__} successfully completed.")
        return

    def set_config_model(self, config_model: BaseConfig):
        self._config_model = config_model
        return self

    def set_logging_db_scraper(self, scraper: str):
        self._logging_db_scraper = scraper
        return self

    def set_driver(self, driver: SB):
        self._driver = driver
        return self

    def _run_scraping(self) -> Any | None:
        from helper.utils import get_sb_configuration

        with SB(**get_sb_configuration()) as self._driver:
            self._driver.activate_cdp_mode()
            self._driver.cdp.maximize()
            return self.scrape()

    def _scrape_url(self, url: str, pause_time: int = 2) -> BeautifulSoup:
        """
        Scrape the URL using Selenium and BeautifulSoup.

        Args:
            url (str): url contains volume and issue number. Eg: https://www.mdpi.com/2072-4292/1/3
            pause_time (int): time to pause between scrolls

        Returns:
            BeautifulSoup: the fully rendered HTML of the URL.
        """
        self._driver.cdp.open(url)
        self._driver.sleep(1)
        self._driver.uc_gui_click_captcha()
        self._wait_for_page_load()

        # Handle cookie popup only once, for the first request
        if self._config_model.cookie_selector:
            self._driver.cdp.click_if_visible(self._config_model.cookie_selector)

        # if a modal exists, find the button with the class `btn-close` and click it
        self._driver.cdp.click_if_visible("div.modal_content button.btn-close")
        self._driver.sleep(random.uniform(0.5, 1.5))

        # Scroll through the page to load all articles
        last_height = self._driver.execute_script(f"""
            function getScrollableElement() {{
                const elements = document.querySelectorAll('*');
                for (const element of elements) {{
                    if (element.scrollHeight > element.clientHeight) {{
                        return element;
                    }}
                }}
                return null;
            }}
            const scrollable = getScrollableElement();
            return scrollable ? scrollable.scrollHeight : document.body.scrollHeight;
        """)

        while True:
            # Scroll down to the bottom
            self._driver.execute_script(f"""
                if (scrollable) {{
                    scrollable.scrollTop = scrollable.scrollHeight;
                }} else {{
                    window.scrollTo(0, document.body.scrollHeight);
                }}
            """)
            self._driver.sleep(pause_time)

            if self._config_model.read_more_button:
                self._driver.cdp.click_if_visible(
                    f"{self._config_model.read_more_button.selector}:contains('{self._config_model.read_more_button.text}')"
                )

            # Calculate new scroll height and compare with the last height
            new_height = self._driver.execute_script("return scrollable ? scrollable.scrollHeight : document.body.scrollHeight;")
            if new_height == last_height:
                break
            last_height = new_height

        # Sleep for some time to avoid being blocked by the server on the next request
        self._driver.sleep(random.uniform(2, 5))

        # Get the fully rendered HTML
        return self._get_parsed_page_source()

    def _wait_for_page_load(self, timeout: int | None = 20):
        if self._config_model.loading_tag:
            self._driver.cdp.assert_element_absent(self._config_model.loading_tag, timeout=timeout)

        if self._config_model.waited_tag:
            self._driver.cdp.wait_for_element_visible(self._config_model.waited_tag, timeout=timeout)

    def _get_parsed_page_source(self) -> BeautifulSoup:
        """
        Get the page source parsed by BeautifulSoup.

        Returns:
            BeautifulSoup: The parsed page source.
        """
        return BeautifulSoup(self._driver.cdp.get_page_source(), "html.parser")

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
                self._logging_db_scraper, link, self._config_model
            )
            self._upload_resource_to_s3(current_resource, link)

            # Sleep after each successful upload to avoid overwhelming the server
            time.sleep(random.uniform(2, 5))

    def _upload_resource_to_s3(self, resource: UploadedResource, resource_name: str) -> int | None:
        if resource.id and resource.success:
            self._logger.warning(f"Resource {resource_name} was already successfully uploaded, skipping.")
            return None

        main_folder: Final[str] = os.getenv("AWS_MAIN_FOLDER", "raw_data")
        resource.bucket_key = resource.bucket_key.format(main_folder=main_folder)
        resource.content_retrieved = True if resource.content else False

        if resource.content:
            resource.success = self._s3_client.upload_content(resource)
        else:
            self._logger.warning(f"We were unable to retrieve the content from {resource_name}, skipping upload.")
            resource.success = False

        return self._uploaded_resource_repository.upsert(
            resource, {"sha256": resource.sha256}, keys_to_purge=["content"]
        )

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


class BaseMappedSubScraper(ABC):
    pass
