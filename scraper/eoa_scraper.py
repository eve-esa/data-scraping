import random
import time
from typing import Type, List

from helper.utils import parse_google_drive_link, get_scraped_url_by_web_element
from model.eoa_models import EOAConfig
from scraper.base_scraper import BaseScraper


class EOAScraper(BaseScraper):
    @property
    def config_model_type(self) -> Type[EOAConfig]:
        return EOAConfig

    def scrape(self) -> List[str] | None:
        pdf_links = []
        for source in self._config_model.sources:
            try:
                self._scrape_url(source.url)

                # with Selenium, look for all "a" tags with "drive.google.com" in "href" and containing the "low" within the lowercased text
                tags = self._driver.cdp.find_elements(
                    "//a[contains(@href, 'drive.google.com') and contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'low')]"
                )

                pdf_links.extend([get_scraped_url_by_web_element(tag, self._config_model.base_url) for tag in tags])
            except Exception as e:
                self._log_and_save_failure(source.url, f"An error occurred while scraping the URL: {source.url}. Error: {e}")

        return pdf_links if pdf_links else None

    def post_process(self, scrape_output: List[str]) -> List[str]:
        return scrape_output

    def upload_to_s3(self, sources_links: List[str]):
        download_urls = []

        for link in sources_links:
            try:
                self._logger.info(f"Parsing Google Drive link {link}")
                _, download_url = parse_google_drive_link(link)
                download_urls.append(download_url)
            except Exception as e:
                self._logger.error(f"Error while parsing Google Drive link {link}: {e}")

            # Sleep after each successful upload to avoid overwhelming the server
            time.sleep(random.uniform(2, 5))

        super().upload_to_s3(download_urls)
