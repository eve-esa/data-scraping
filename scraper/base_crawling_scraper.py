from abc import abstractmethod
import os
import random
import shutil
import time
from typing import Type, List
from scrapy.crawler import CrawlerProcess

from model.base_crawling_models import BaseCrawlingConfig, BaseCrawlingScraperOutput
from scraper.base_scraper import BaseScraper
from service.crawler import EveSpider


class BaseCrawlingScraper(BaseScraper):
    @property
    def config_model_type(self) -> Type[BaseCrawlingConfig]:
        return BaseCrawlingConfig

    def scrape(self) -> BaseCrawlingScraperOutput | None:
        """
        Scrape the website, even better crawl the website.

        Returns:
            BaseCrawledPublisherScraperOutput: The output of the scraper, or None if the scraping failed.
        """
        start_urls = [source.url for source in self._config_model.sources]
        if not start_urls:
            self._logger.error("No start URLs provided in the configuration model.")
            return None

        process = CrawlerProcess()

        self._logger.info("Starting the crawling process.")
        process.crawl(EveSpider, start_urls=start_urls, download_folder_path=self.crawling_folder_path)
        process.start()
        process.join()

        # log the end of the crawling process
        self._logger.info("Crawling process completed successfully.")

        return {source.name: source.url for source in self._config_model.sources}

    def post_process(self, scrape_output: BaseCrawlingScraperOutput) -> List[str]:
        return list(scrape_output.values())

    def upload_to_s3(self, sources_links: List[str]):
        self._logger.debug("Uploading files to S3")

        file_paths = [
            os.path.join(self.crawling_folder_path, file)
            for file in os.listdir(self.crawling_folder_path)
            if file.endswith(self._config_model.file_extension)
            and os.path.isfile(os.path.join(self.crawling_folder_path, file))
        ]
        if not file_paths:
            for source_link in sources_links:
                self._save_failure(source_link, f"No files found in the crawling folder: {source_link}")

        for file_path in file_paths:
            current_resource = self._uploaded_resource_repository.get_by_content(
                self._logging_db_scraper, self._config_model.bucket_key, file_path
            )
            if not self._check_valid_resource(current_resource, file_path.replace(self.crawling_folder_path, "")):
                continue

            self._upload_resource_to_s3_and_store_to_db(current_resource)

            # Sleep after each successful download to avoid overwhelming the server
            time.sleep(random.uniform(2, 5))

        # remove the entire download folder
        shutil.rmtree(self.crawling_folder_path)

    @property
    @abstractmethod
    def crawling_folder_path(self) -> str:
        """
        The folder path where the crawling files are stored. This property must be implemented in the derived class.

        Returns:
            str: The folder path.
        """
        pass
