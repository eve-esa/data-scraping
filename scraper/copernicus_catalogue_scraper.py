import os
import random
import shutil
import time
from typing import Type, List
from uuid import uuid4
from bs4 import Tag

from helper.utils import get_scraped_url_by_bs_tag, get_scraped_url_by_web_element
from model.base_pagination_publisher_models import BasePaginationPublisherScrapeOutput, BasePaginationPublisherConfig
from scraper.base_pagination_publisher_scraper import BasePaginationPublisherScraper


class CopernicusCatalogueScraper(BasePaginationPublisherScraper):
    def __init__(self):
        super().__init__()
        self.__download_folder_path = None

    @property
    def config_model_type(self) -> Type[BasePaginationPublisherConfig]:
        return BasePaginationPublisherConfig

    def scrape(self) -> BasePaginationPublisherScrapeOutput | None:
        pdf_tags = []
        for idx, source in enumerate(self._config_model.sources):
            pdf_tags.extend(self._scrape_landing_page(source.landing_page_url, idx + 1))

        return {"Copernicus Service Catalogues": [
            get_scraped_url_by_bs_tag(tag, self._config_model.base_url) for tag in pdf_tags
        ]} if pdf_tags else None

    def _scrape_landing_page(self, landing_page_url: str, source_number: int) -> List[Tag]:
        self._logger.info(f"Processing Landing Page {landing_page_url}")

        return self._scrape_pagination(landing_page_url, source_number, base_zero=True)

    def _scrape_page(self, url: str) -> List[Tag] | None:
        try:
            self._scrape_url(url)
            if not (article_tags := self._driver.cdp.find_elements("div.service-catalogue-item a")):
                self._save_failure(url)

            html_tag_list = []
            for article_tag in article_tags:
                # for each article, visit the URL and click on the "Read more" button if it exists
                article_url = get_scraped_url_by_web_element(article_tag, self._config_model.base_url)
                self._logger.info(f"Processing Catalogue URL: {article_url}")

                self._driver.cdp.open(article_url)
                self._driver.cdp.sleep(1)
                self._driver.cdp.click_if_visible("a.ec-toggle-link.ecf-open")

                # write the HTML source to a file
                with open(os.path.join(self.download_folder_path, f"{uuid4()}.html"), "w") as f:
                    f.write(self._driver.get_page_source())

                # now, check if there is a link to an external source within the article
                try:
                    external_url = get_scraped_url_by_web_element(
                        self._driver.cdp.find_element("a.btn-outline-primary"), self._config_model.base_url
                    )
                    # if the external URL is the same as the article URL, skip it
                    if external_url == article_url:
                        continue

                    self._logger.info(f"Processing Catalogues Source URL: {external_url}")

                    # visit the external URL and click on the buttons to see the full content of the page
                    self._driver.cdp.open(external_url)
                    self._driver.cdp.sleep(1)
                    self._driver.cdp.click_if_visible("button:contains('Accept all')")
                    self._driver.cdp.sleep(1)
                    self._driver.cdp.click_if_visible("button:contains('Overview')")
                    self._driver.cdp.sleep(1)
                    self._driver.cdp.click_if_visible("span:contains('Read more')")

                    # write the HTML source to a file
                    with open(os.path.join(self.download_folder_path, f"{uuid4()}.html"), "w") as f:
                        f.write(self._driver.get_page_source())

                    html_tag_list.append(Tag(name="a", attrs={"href": external_url}))
                except Exception:
                    pass

                html_tag_list.append(Tag(name="a", attrs={"href": article_url}))

            self._logger.debug(f"PDF links found: {len(html_tag_list)}")
            return html_tag_list
        except Exception as e:
            self._log_and_save_failure(url, f"Failed to process URL {url}. Error: {e}")
            return None

    def upload_to_s3(self, sources_links: List[str]):
        self._logger.debug("Uploading files to S3")
        download_folder = self.download_folder_path

        file_paths = [
            os.path.join(download_folder, file)
            for file in os.listdir(download_folder)
            if file.endswith(self._config_model.file_extension)
               and os.path.isfile(os.path.join(download_folder, file))
        ]
        if not file_paths:
            for source_link in sources_links:
                self._save_failure(source_link, f"No files found in the downloading folder: {source_link}")

        for file_path in file_paths:
            current_resource = self._uploaded_resource_repository.get_by_content(
                self._logging_db_scraper, self._config_model.bucket_key, file_path
            )
            self._upload_resource_to_s3(current_resource, file_path.replace(download_folder, ""))

            # Sleep after each successful upload to avoid overwhelming the server
            time.sleep(random.uniform(2, 5))

        shutil.rmtree(self.download_folder_path)

    @property
    def download_folder_path(self) -> str:
        if self.__download_folder_path is None:
            download_folder_path = os.path.join(self._driver.get_browser_downloads_folder(), "copernicus")
            os.makedirs(download_folder_path, exist_ok=True)

            self.__download_folder_path = download_folder_path

        return self.__download_folder_path
