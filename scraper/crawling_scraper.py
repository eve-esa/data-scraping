import os
import random
import shutil
import time
from typing import Type, List
from scrapy.crawler import CrawlerProcess

from model.crawling_models import CrawlingConfig, CrawlingScraperOutput
from scraper.base_scraper import BaseScraper
from service.crawler import EveSpider


class CrawlingScraper(BaseScraper):
    def __init__(self):
        super().__init__()

        self._download_folder_path = os.path.join(self._download_folder_path, "crawled")

    @property
    def config_model_type(self) -> Type[CrawlingConfig]:
        return CrawlingConfig

    def scrape(self, model: CrawlingConfig) -> CrawlingScraperOutput | None:
        """
        Scrape the website, even better crawl the website.

        Args:
            model (CrawlingConfig): The configuration model.

        Returns:
            BaseCrawledPublisherScraperOutput: The output of the scraper, or None if the scraping failed.
        """
        start_urls = [source.url for source in model.sources]
        if not start_urls:
            self._logger.error("No start URLs provided in the configuration model.")
            return None

        process = CrawlerProcess()

        self._logger.info("Starting the crawling process.")
        process.crawl(EveSpider, start_urls=start_urls, download_folder_path=self._download_folder_path)
        process.start()
        process.join()

        # log the end of the crawling process
        self._logger.info("Crawling process completed successfully.")

        return {source.name: source.url for source in model.sources}

    def post_process(self, scrape_output: CrawlingScraperOutput) -> List[str]:
        return list(scrape_output.values())

    def _upload_to_s3(self, sources_links: List[str]) -> bool:
        self._logger.debug("Uploading files to S3")

        all_done = True

        # upload files to S3
        for file in os.listdir(self._download_folder_path):
            if not os.path.isfile(os.path.join(self._download_folder_path, file)):
                continue

            if not file.endswith(self.file_extension):
                continue

            with open(os.path.join(self._download_folder_path, file), "rb") as f:
                result = self._s3_client.upload_content(self.bucket_key, file, f.read())
                if not result:
                    all_done = False

            # Sleep after each successful download to avoid overwhelming the server
            time.sleep(random.uniform(2, 5))

        # remove the entire download folder
        shutil.rmtree(self._download_folder_path)

        return all_done
