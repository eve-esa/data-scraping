from typing import Type, List
from bs4 import ResultSet, Tag

from helper.utils import get_scraped_url_by_bs_tag
from model.base_pagination_publisher_models import BasePaginationPublisherScrapeOutput, BasePaginationPublisherConfig
from scraper.base_pagination_publisher_scraper import BasePaginationPublisherScraper


class AMSScraper(BasePaginationPublisherScraper):
    @property
    def config_model_type(self) -> Type[BasePaginationPublisherConfig]:
        return BasePaginationPublisherConfig

    def scrape(self) -> BasePaginationPublisherScrapeOutput | None:
        pdf_tags = []
        for idx, source in enumerate(self._config_model.sources):
            pdf_tags.extend(self._scrape_landing_page(source.landing_page_url, idx + 1))

        return {"AMS": [
            get_scraped_url_by_bs_tag(tag, self._config_model.base_url) for tag in pdf_tags
        ]} if pdf_tags else None

    def _scrape_landing_page(self, landing_page_url: str, source_number: int) -> List[Tag]:
        return self._scrape_pagination(landing_page_url, source_number)

    def _scrape_page(self, url: str) -> ResultSet | List[Tag] | None:
        try:
            scraper = self._scrape_url(url)

            results_block = scraper.find("div", class_=lambda class_: class_ and "results-column" in class_)
            if not results_block:
                raise Exception(f"Results not found in URL {url}")

            # Find all PDF links using appropriate class or tag (if lambda returns True, it will be included in the list)
            if not (pdf_tag_list := scraper.find_all(
                    "a",
                    href=lambda href: href and "/downloadpdf/" in href,
                    class_=lambda class_: class_ and "pdf-download" in class_
            )):
                self._save_failure(url)

            self._logger.debug(f"PDF links found: {len(pdf_tag_list)}")
            return pdf_tag_list
        except Exception as e:
            self._log_and_save_failure(url, f"Failed to process URL {url}. Error: {e}")
            return None

    def _is_valid_tag_list(self, page_tag_list: List | None) -> bool:
        return page_tag_list is not None
