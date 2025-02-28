import os
import random
import time
from abc import ABC, abstractmethod
from typing import List
from seleniumbase import SB

from helper.utils import get_sb_configuration
from scraper.base_scraper import BaseScraper


class BaseSourceDownloadScraper(BaseScraper, ABC):
    def upload_to_s3(self, sources_links: List[str]):
        self._logger.debug("Uploading files to S3")

        sb_configuration = get_sb_configuration()
        sb_configuration["external_pdf"] = True

        with SB(**sb_configuration) as driver:
            self.set_driver(driver)
            self._driver.activate_cdp_mode()
            self._driver.cdp.maximize()

            for link in sources_links:
                self._logger.debug(f"Downloading file from {link}")
                if not (file_path := self._get_file_path_from_link(link)):
                    continue

                current_resource = self._uploaded_resource_repository.get_by_content(
                    self._logging_db_scraper, self._config_model.bucket_key, file_path
                )
                self._upload_resource_to_s3(current_resource, os.path.basename(file_path))

                # remove the file and sleep after each successful upload to avoid overwhelming the server
                os.remove(file_path)
                time.sleep(random.uniform(2, 5))

    def _wait_end_download(
        self, file_identifier: str, timeout: int | None = 30, interval: float | None = 0.5
    ) -> str | None:
        """
        Wait for the download to finish. If the download is not completed within the specified timeout, raise an
        exception.

        Args:
            file_identifier (str): The identifier of the file to download.
            timeout (int): The timeout in seconds. Default is 10 seconds.
            interval (float): The interval in seconds to check for the file. Default is 0.5 seconds.
        """
        start_time = time.time()
        download_folder_path = self._driver.get_browser_downloads_folder()

        # wait until the download is completed
        while time.time() - start_time < timeout:
            time.sleep(interval)
            completed_downloads = sorted(
                [f for f in os.listdir(download_folder_path) if file_identifier in f and ".crdownload" not in f],
                key=lambda x: os.path.getmtime(os.path.join(download_folder_path, x)),
                reverse=True
            )
            if not completed_downloads:
                continue

            # move the downloaded file to the download folder
            file = completed_downloads[0]
            return os.path.join(download_folder_path, file)

        return None

    @abstractmethod
    def _get_file_path_from_link(self, link: str) -> str | None:
        pass
