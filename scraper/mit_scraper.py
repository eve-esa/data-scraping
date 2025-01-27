from typing import List
from bs4 import ResultSet, Tag

from helper.utils import get_scraped_url
from model.base_url_publisher_models import BaseUrlPublisherSource
from scraper.base_url_publisher_scraper import BaseUrlPublisherScraper


class MITScraper(BaseUrlPublisherScraper):
    def _scrape_journal(self, source: BaseUrlPublisherSource) -> ResultSet | List[Tag] | None:
        pass

    def _scrape_issue_or_collection(self, source: BaseUrlPublisherSource) -> List[Tag] | None:
        self._logger.info(f"Processing Issue / Collection {source.url}")

        try:
            scraper = self._scrape_url(source.url)

            pdf_tag_list = [
                pdf_tag for tag in scraper.find_all(
                    "a", href=lambda href: href and "/courses/" in href and "/resources/earthsurface_" in href
                )
                if (pdf_tag := self._scrape_url(get_scraped_url(tag, self.base_url)).find(
                    "a", href=lambda href: href and ".pdf" in href, class_="download-file"
                ))
            ]

            self._logger.debug(f"PDF links found: {len(pdf_tag_list)}")
            return pdf_tag_list
        except Exception as e:
            self._logger.error(f"Failed to process Issue / Collection {source.url}. Error: {e}")
            return None

    def _scrape_article(self, source: BaseUrlPublisherSource) -> Tag | None:
        pass
