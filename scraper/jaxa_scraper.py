from typing import List, Dict
import random
from uuid import uuid4
from bs4 import ResultSet, Tag
import time

from model.base_url_publisher_models import BaseUrlPublisherSource
from scraper.base_url_publisher_scraper import BaseUrlPublisherScraper


class JAXAScraper(BaseUrlPublisherScraper):
    def _scrape_journal(self, source: BaseUrlPublisherSource) -> ResultSet | List[Tag] | None:
        pass

    def _scrape_issue_or_collection(self, source: BaseUrlPublisherSource) -> ResultSet | None:
        self._logger.info(f"Processing Issue / Collection {source.url}")

        try:
            scraper, driver = self._scrape_url(source.url)
            driver.quit()

            # Find all PDF links using appropriate class or tag (if lambda returns True, it will be included in the list)
            html_tag_list = scraper.find_all("a", href=True, class_="btn--outline")

            self._logger.debug(f"HTML links found: {len(html_tag_list)}")
            return html_tag_list
        except Exception as e:
            self._logger.error(f"Failed to process Issue / Collection {source.url}. Error: {e}")
            return None

    def upload_to_s3(self, sources_links: Dict[str, List[str]] | List[str], **kwargs) -> bool:
        """
        Upload the source files to S3.

        Args:
            sources_links (Dict[str, List[str]] | List[str]): The list of links of the various sources.

        Returns:
            bool: True if the upload was successful, False otherwise.
        """
        self._logger.debug("Uploading files to S3")

        all_done = True
        for link in sources_links:
            result = self._s3_client.upload(self.bucket_key, link, self.file_extension)
            if not result:
                all_done = False

                # retrying the upload
                link = link.replace("index.html", f"index_{uuid4()}.html")
                all_done = all_done or self._s3_client.upload(self.bucket_key, link, self.file_extension)

            # Sleep after each successful download to avoid overwhelming the server
            time.sleep(random.uniform(2, 5))

        return all_done

    def _scrape_article(self, source: BaseUrlPublisherSource) -> Tag | None:
        pass
