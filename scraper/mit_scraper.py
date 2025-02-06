from typing import List, Type
from bs4 import ResultSet, Tag

from helper.utils import get_scraped_url
from model.base_url_publisher_models import BaseUrlPublisherSource, BaseUrlPublisherConfig
from scraper.base_url_publisher_scraper import BaseUrlPublisherScraper


class MITScraper(BaseUrlPublisherScraper):
    @property
    def config_model_type(self) -> Type[BaseUrlPublisherConfig]:
        """
        Return the configuration model type.

        Returns:
            Type[BaseUrlPublisherConfig]: The configuration model type
        """
        return BaseUrlPublisherConfig

    def _scrape_journal(self, source: BaseUrlPublisherSource) -> ResultSet | List[Tag] | None:
        pass

    def _scrape_issue_or_collection(self, source: BaseUrlPublisherSource) -> List[Tag] | None:
        self._logger.info(f"Processing Issue / Collection {source.url}")

        try:
            scraper, driver = self._scrape_url(source.url)
            driver.quit()

            pdf_tag_list = []
            for tag in scraper.find_all("a", href=lambda href: href and "/courses/" in href and "/resources/earthsurface_" in href):
                scraper_inner, driver_inner = self._scrape_url(get_scraped_url(tag, self._config_model.base_url))
                driver_inner.quit()
                if pdf_tag := scraper.find("a", href=lambda href: href and ".pdf" in href, class_="download-file"):
                    pdf_tag_list.append(pdf_tag)

            if not pdf_tag_list:
                self._save_failure(source.url)

            self._logger.debug(f"PDF links found: {len(pdf_tag_list)}")
            return pdf_tag_list
        except Exception as e:
            self._log_and_save_failure(source.url, f"Failed to process Issue / Collection {source.url}. Error: {e}")
            return None

    def _scrape_article(self, source: BaseUrlPublisherSource) -> Tag | None:
        pass
