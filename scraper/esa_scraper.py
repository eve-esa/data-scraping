from typing import List, Type, Dict
from bs4 import Tag, ResultSet

from model.base_mapped_models import BaseMappedUrlSource
from scraper.base_mapped_publisher_scraper import BaseMappedPublisherScraper
from scraper.base_scraper import BaseMappedScraper
from scraper.base_url_publisher_scraper import BaseUrlPublisherScraper


class ESAScraper(BaseMappedPublisherScraper):
    @property
    def mapping(self) -> Dict[str, Type[BaseMappedScraper]]:
        return {"EsaUrlScraper": ESAUrlScraper}


class ESAUrlScraper(BaseUrlPublisherScraper, BaseMappedScraper):
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
