import random
import time
from abc import abstractmethod
from typing import List, Type, Dict

from model.base_mapped_models import BaseMappedConfig
from scraper.base_scraper import BaseScraper, BaseMappedSubScraper
from service.adapter import ScrapeAdapter


class BaseMappedPublisherScraper(BaseScraper):
    def __init__(self):
        super().__init__()

        self._bucket_keys = {}
        self._file_extensions = {}

    @property
    @abstractmethod
    def mapping(self) -> Dict[str, Type[BaseMappedSubScraper]]:
        """
        Return the mapping of the scraper to the source. This method must be implemented in the derived class.

        Returns:
            Dict[str, Type[BaseMappedSubScraper]]: The mapping of the scraper to the source
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

    def scrape(self) -> Dict[str, List[str] | Dict[str, List[str]]] | None:
        """
        Scrape the resources links.

        Returns:
            Dict[str, List | Dict]: The output of the scraping.
        """
        links = {}
        for source in self._config_model.sources:
            self._logger.info(f"Processing source {source.name}")

            results = ScrapeAdapter(source.config, self.__class__.__name__, self.mapping.get(source.scraper)).scrape()
            if results is not None:
                links[source.name] = results
                self._bucket_keys[source.name] = f"{self._config_model.bucket_key}/{source.config.bucket_key or ''}".rstrip("/")
                self._file_extensions[source.name] = source.config.file_extension or self._config_model.file_extension

        return links if links else None

    def post_process(self, scrape_output: Dict[str, List[str] | Dict[str, List[str]]]) -> Dict[str, List[str]]:
        """
        Post-process the scraped output. This method is called after the sources have been scraped. It is used to
        retrieve the final list of processed URLs. This method must be implemented in the derived class.

        Args:
            scrape_output (Dict[str, List[str] | Dict[str, List[str]]]): The scraped output

        Returns:
            Dict[str, List[str]]: The results of the scraping
        """
        return {
            source.name: ScrapeAdapter(
                source.config, self.__class__.__name__, self.mapping.get(source.scraper)
            ).post_process(scrape_output[source.name])
            for source in self._config_model.sources if source.name in scrape_output
        }

    def upload_to_s3(self, sources_links: Dict[str, List[str]]):
        for source in self._config_model.sources:
            if source.name not in sources_links:
                continue

            ScrapeAdapter(source.config, self.__class__.__name__, self.mapping.get(source.scraper)).upload_to_s3(
                sources_links[source.name],
                self._bucket_keys[source.name],
                self._file_extensions[source.name],
            )

            # Sleep after each successful download to avoid overwhelming the server
            time.sleep(random.uniform(2, 5))
