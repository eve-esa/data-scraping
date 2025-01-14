import random
import time
from abc import abstractmethod
from typing import List, Type, Dict

from model.base_mapped_models import BaseMappedConfig
from scraper.base_scraper import BaseScraper, BaseMappedScraper
from service.adapter import ScrapeAdapter


class BaseMappedPublisherScraper(BaseScraper):
    def __init__(self):
        super().__init__()

        self.__bucket_keys = {}
        self.__file_extensions = {}

    @property
    @abstractmethod
    def mapping(self) -> Dict[str, Type[BaseMappedScraper]]:
        """
        Return the mapping of the scraper to the source. This method must be implemented in the derived class.

        Returns:
            Dict[str, Type[BaseMappedScraper]]: The mapping of the scraper to the source
        """
        pass

    @property
    def config_model_type(self) -> Type[BaseMappedConfig]:
        """
        Return the configuration model type.

        Returns:
            Type[BaseMappedConfig]: The configuration model type
        """
        return BaseMappedConfig

    def scrape(self, model: BaseMappedConfig) -> Dict[str, List[str] | Dict[str, List[str]]]:
        """
        Scrape the resources links.

        Args:
            model (BaseMappedConfig): The configuration model.

        Returns:
            Dict[str, List | Dict]: The output of the scraping.
        """
        links = {}
        for source in model.sources:
            self._logger.info(f"Processing source {source.name}")

            results = ScrapeAdapter(source.config, self.mapping.get(source.scraper)).scrape()
            if results is not None:
                links[source.name] = results
                self.__bucket_keys[source.name] = f"{self.bucket_key}/{source.config.bucket_key or ''}".rstrip("/")
                self.__file_extensions[source.name] = source.config.file_extension or self.file_extension

        return links

    def post_process(self, scrape_output: Dict[str, List[str] | Dict[str, List[str]]]) -> Dict[str, List[str]]:
        """
        Post-process the scraped output. This method is called after the sources have been scraped. It is used to
        retrieve the final list of processed URLs. This method must be implemented in the derived class.

        Args:
            scrape_output (Dict[str, List[str] | Dict[str, List[str]]]): The scraped output

        Returns:
            Dict[str, List[str]]: The results of the scraping
        """
        return {source_name: source_links if isinstance(source_links, list) else [
                link for links in source_links.values() for link in links
            ] for source_name, source_links in scrape_output.items()}

    def _upload_to_s3(self, sources_links: Dict[str, List[str]]) -> bool:
        """
        Upload the source files to S3.

        Args:
            sources_links (Dict[str, List[str]]): The list of links of the various sources.

        Returns:
            bool: True if the upload was successful, False otherwise.
        """
        self._logger.info("Uploading files to S3")

        all_done = True
        for source_name, source_links in sources_links.items():
            bucket_key = self.__bucket_keys[source_name]
            file_extension = self.__file_extensions[source_name]

            for link in source_links:
                result = self._s3_client.upload(bucket_key, link, file_extension)
                if not result:
                    all_done = False

                # Sleep after each successful download to avoid overwhelming the server
                time.sleep(random.uniform(2, 5))

        return all_done
