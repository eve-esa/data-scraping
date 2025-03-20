from typing import List, Type
from bs4 import Tag, ResultSet

from helper.utils import get_scraped_url_by_bs_tag
from model.base_url_publisher_models import BaseUrlPublisherSource, SourceType, BaseUrlPublisherConfig
from scraper.base_url_publisher_scraper import BaseUrlPublisherScraper


class EOGEScraper(BaseUrlPublisherScraper):
    @property
    def config_model_type(self) -> Type[BaseUrlPublisherConfig]:
        return BaseUrlPublisherConfig

    def _scrape_journal(self, source: BaseUrlPublisherSource) -> List[Tag] | None:
        self._logger.info(f"Processing Journal {source.url}")

        try:
            self._scrape_url(source.url)

            # Click all the volume links to load all the issues
            buttons = self._driver.cdp.find_elements('a[data-toggle="collapse"]:not(.collapsed)', timeout=0.5)
            for button in buttons:
                button.click()
                self._driver.sleep(1)

            # Find all PDF links using appropriate class or tag (if lambda returns True, it will be included in the list)
            issues_tag_list = self._get_parsed_page_source().find_all(
                "a", href=lambda href: href and "issue_" in href and ".html" in href
            )

            # For each tag of issues previously collected, scrape the issue as a collection of articles
            pdf_tag_list = [
                tag
                for tags in (
                    self._scrape_issue_or_collection(BaseUrlPublisherSource(
                        url=get_scraped_url_by_bs_tag(tag, self._config_model.base_url),
                        type=str(SourceType.ISSUE_OR_COLLECTION)
                    ))
                    for tag in issues_tag_list
                )
                if tags for tag in tags
            ]

            self._logger.debug(f"PDF links found: {len(pdf_tag_list)}")
            return pdf_tag_list
        except Exception as e:
            self._log_and_save_failure(source.url, f"Failed to process Journal {source.url}. Error: {e}")
            return None

    def _scrape_issue_or_collection(self, source: BaseUrlPublisherSource) -> ResultSet | None:
        self._logger.info(f"Processing Issue / Collection {source.url}")

        try:
            scraper = self._scrape_url(source.url)

            # Find all PDF links using appropriate class or tag (if lambda returns True, it will be included in the list)
            if not (pdf_tag_list := scraper.find_all(
                "a", href=lambda href: href and "/article" in href and ".pdf" in href, class_="pdf_link"
            )):
                self._save_failure(source.url)

            self._logger.debug(f"PDF links found: {len(pdf_tag_list)}")
            return pdf_tag_list
        except Exception as e:
            self._log_and_save_failure(source.url, f"Failed to process Issue / Collection {source.url}. Error: {e}")
            return None

    def _scrape_article(self, source: BaseUrlPublisherSource) -> Tag | None:
        pass