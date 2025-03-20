from typing import Type
from bs4 import ResultSet

from helper.utils import get_scraped_url_by_bs_tag
from model.base_pagination_publisher_models import BasePaginationPublisherScrapeOutput
from model.ncbi_models import NCBIConfig
from scraper.base_pagination_publisher_scraper import BasePaginationPublisherScraper


class NCBIScraper(BasePaginationPublisherScraper):
    @property
    def config_model_type(self) -> Type[NCBIConfig]:
        return NCBIConfig

    def scrape(self) -> BasePaginationPublisherScrapeOutput | None:
        pdf_tags = []
        for idx, source in enumerate(self._config_model.sources):
            self._scrape_landing_page(source.landing_page_url, idx + 1)
            pdf_tags.extend(self._scrape_pagination(source.pagination_url, idx + 1))

        return {"NCBI": [
            get_scraped_url_by_bs_tag(tag, self._config_model.base_url) for tag in pdf_tags
        ]} if pdf_tags else None

    def _scrape_landing_page(self, landing_page_url: str, source_number: int) -> None:
        self._logger.info(f"Processing Landing Page {landing_page_url}")
        self._scrape_url(landing_page_url)

    def _scrape_page(self, url: str) -> ResultSet | None:
        try:
            scraper = self._scrape_url(url)

            # Find all PDF links using appropriate class or tag (if lambda returns True, it will be included in the list)
            if not (pdf_tag_list := scraper.find_all(
                    "a", href=lambda href: href and "/articles/" in href and ".pdf" in href, class_="view"
            )):
                self._save_failure(url)

            self._logger.debug(f"PDF links found: {len(pdf_tag_list)}")
            return pdf_tag_list
        except Exception as e:
            self._log_and_save_failure(url, f"Failed to process URL {url}. Error: {e}")
            return None
