import random
import time
from typing import List, Type, Dict
from bs4 import Tag, ResultSet

from model.base_mapped_models import BaseMappedUrlSource, BaseMappedConfig, SourceType
from scraper.base_scraper import BaseScraper, BaseMappedScraper
from scraper.base_url_publisher_scraper import BaseUrlPublisherScraper
from service.adapter import ScrapeAdapter


class ESAScraper(BaseScraper):
    def __init__(self):
        super().__init__()

        self.__file_extensions = {}

    def setup_driver(self):
        pass

    @property
    def config_model_type(self) -> Type[BaseMappedConfig]:
        """
        Return the configuration model type.

        Returns:
            Type[BaseMappedConfig]: The configuration model type
        """
        return BaseMappedConfig

    def scrape(self, model: BaseMappedConfig) -> Dict[str, List]:
        """
        Scrape the resources links.

        Args:
            model (BaseMappedConfig): The configuration model.

        Returns:
            Dict[str, List]: The output of the scraping.
        """
        pdf_links = {}
        mapping = {str(SourceType.URL): EsaUrlScraper}
        for source in model.sources:
            self._logger.info(f"Processing source {source.name}")

            results = ScrapeAdapter(source, mapping).scrape()
            if results is not None:
                pdf_links[source.name] = results
                self.__file_extensions[source.name] = source.config.file_extension

        return pdf_links

    def post_process(self, scrape_output: Dict[str, List]) -> Dict[str, List[str]]:
        """
        Post-process the scraped output. This method is called after the sources have been scraped. It is used to
        retrieve the final list of processed URLs. This method must be implemented in the derived class.

        Args:
            scrape_output (Dict[str, List]): The scraped output

        Returns:
            Dict[str, List[str]]: The results of the scraping
        """
        return scrape_output

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
            file_extension = self.__file_extensions[source_name]

            for link in source_links:
                result = self._s3_client.upload(self.bucket_key, link, file_extension)
                if not result:
                    all_done = False

                # Sleep after each successful download to avoid overwhelming the server
                time.sleep(random.uniform(2, 5))

        return all_done


class EsaUrlScraper(BaseUrlPublisherScraper, BaseMappedScraper):
    def _scrape_journal(self, source: BaseMappedUrlSource) -> ResultSet | List[Tag] | None:
        pass

    def _scrape_issue_or_collection(self, source: BaseMappedUrlSource) -> ResultSet | List[Tag] | None:
        self._logger.info(f"Processing Issue / Collection {source.url}")

        try:
            scraper = self._scrape_url(source.url)

            href_fnc = lambda href: href and source.href in href and "##" not in href

            # Find all PDF links using appropriate class or tag (if lambda returns True, it will be included in the list)
            if source.class_:
                pdf_tag_list = scraper.find_all("a", href=href_fnc, class_=source.class_)
            else:
                pdf_tag_list = scraper.find_all("a", href=href_fnc)
            self._logger.info(f"PDF links found: {len(pdf_tag_list)}")

            return pdf_tag_list
        except Exception as e:
            self._logger.error(f"Failed to process Issue / Collection {source.url}. Error: {e}")
            return None

    def _scrape_article(self, source: BaseMappedUrlSource) -> Tag | None:
        pass
