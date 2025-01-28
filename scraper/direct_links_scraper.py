import random
import time
from typing import Dict, Type, List

from scraper.base_mapped_publisher_scraper import BaseMappedPublisherScraper
from scraper.base_scraper import BaseMappedScraper


class DirectLinksScraper(BaseMappedPublisherScraper):
    @property
    def mapping(self) -> Dict[str, Type[BaseMappedScraper]]:
        return {}

    def upload_to_s3(self, sources_links: Dict[str, List[str]] | List[str], **kwargs) -> bool:
        """
        Upload the source files to S3.

        Args:
            sources_links (Dict[str, List[str]] | List[str]): The list of links of the various sources.

        Returns:
            bool: True if the upload was successful, False otherwise.
        """
        self._logger.debug("Uploading files to S3")

        if isinstance(sources_links, list):
            bucket_key = kwargs.get("bucket_key")
            file_extension = kwargs.get("file_extension")
            all_done = self.__upload_to_s3_from_list(sources_links, bucket_key, file_extension)
        else:
            all_done = self.__upload_to_s3_from_dict(sources_links)

        return all_done

    def __upload_to_s3_from_list(self, source_links: List[str], bucket_key: str, file_extension: str) -> bool:
        all_done = True
        for link in source_links:
            result = self._s3_client.upload(bucket_key, link, file_extension)
            if not result:
                all_done = False

            # Sleep after each successful download to avoid overwhelming the server
            time.sleep(random.uniform(2, 5))

        return all_done

    def __upload_to_s3_from_dict(self, sources_links: Dict[str, List[str]]) -> bool:
        all_done = True
        for source_name, source_links in sources_links.items():
            bucket_key = self._bucket_keys[source_name]
            file_extension = self._file_extensions[source_name]

            for link in source_links:
                result = self._s3_client.upload(bucket_key, link, file_extension)
                if not result:
                    all_done = False

                # Sleep after each successful download to avoid overwhelming the server
                time.sleep(random.uniform(2, 5))

        return all_done