import random
import time
from typing import Type, List
import requests
from bs4 import Tag
from selenium.webdriver.common.by import By

from helper.utils import get_scraped_url, get_filename, parse_google_drive_link
from model.eoa_models import EOAConfig
from scraper.base_scraper import BaseScraper


class EOAScraper(BaseScraper):
    @property
    def config_model_type(self) -> Type[EOAConfig]:
        return EOAConfig

    def scrape(self, model: EOAConfig) -> List[str] | None:
        pdf_links = []
        for source in model.sources:
            try:
                _, driver = self._scrape_url(source.url)

                # with Selenium, look for all "a" tags with "drive.google.com" in "href" and containing the "low" within the lowercased text
                tags = driver.find_elements(
                    By.XPATH,
                    "//a[contains(@href, 'drive.google.com') and contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'low')]"
                )
                driver.quit()

                pdf_links.extend([
                    get_scraped_url(Tag(name="a", attrs={"href": tag.get_attribute("href")}), self.base_url)
                    for tag in tags
                ])
            except Exception as e:
                print(f"An error occurred while scraping the URL: {source.url}. Error: {e}")

        return pdf_links if pdf_links else None

    def post_process(self, scrape_output: List[str]) -> List[str]:
        return scrape_output

    def _upload_to_s3(self, sources_links: List[str]) -> bool:
        self._logger.debug("Uploading files to S3")

        all_done = True
        for link in sources_links:
            try:
                file_id, download_url = parse_google_drive_link(link)

                self._logger.info(f"Retrieving file from {download_url}")

                response = requests.get(download_url, stream=True)
                response.raise_for_status()

                result = self._s3_client.upload_content(
                    self.bucket_key, get_filename(file_id, self.file_extension), response.content
                )
                if not result:
                    all_done = False
            except Exception as e:
                self._logger.error(f"Error uploading file to S3: {e}")
                all_done = False

            # Sleep after each successful download to avoid overwhelming the server
            time.sleep(random.uniform(2, 5))

        return all_done
