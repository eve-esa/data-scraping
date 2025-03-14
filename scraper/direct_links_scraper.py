from typing import Dict, Type, List

from scraper.base_mapped_publisher_scraper import BaseMappedPublisherScraper
from scraper.base_scraper import BaseMappedSubScraper


class DirectLinksScraper(BaseMappedPublisherScraper):
    @property
    def mapping(self) -> Dict[str, Type[BaseMappedSubScraper]]:
        return {}

    def upload_to_s3(self, sources_links: Dict[str, List[str]] | List[str]):
        if isinstance(sources_links, list):
            return super(BaseMappedPublisherScraper, self).upload_to_s3(sources_links)

        for source_name, source_links in sources_links.items():
            current_config_model = self._config_model.model_copy()
            self._config_model.bucket_key = self._bucket_keys[source_name]
            self._config_model.files_by_request = self._files_by_request[source_name]

            super(BaseMappedPublisherScraper, self).upload_to_s3(source_links)
            self.set_config_model(current_config_model)
