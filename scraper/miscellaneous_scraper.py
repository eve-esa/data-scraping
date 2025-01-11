from typing import List, Dict, Type
from bs4 import ResultSet, Tag
from selenium.webdriver.common.by import By

from helper.utils import get_scraped_url
from model.base_mapped_models import BaseMappedUrlSource
from scraper.base_mapped_publisher_scraper import BaseMappedPublisherScraper
from scraper.base_scraper import BaseMappedScraper
from scraper.base_url_publisher_scraper import BaseUrlPublisherScraper


class MiscellaneousScraper(BaseMappedPublisherScraper):
    @property
    def mapping(self) -> Dict[str, Type[BaseMappedScraper]]:
        return {
            "OpenNightLightsScraper": OpenNightLightsScraper,
            "WikipediaScraper": WikipediaScraper,
        }


class OpenNightLightsScraper(BaseUrlPublisherScraper, BaseMappedScraper):
    def _scrape_journal(self, source: BaseMappedUrlSource) -> ResultSet | List[Tag] | None:
        pass

    def _scrape_issue_or_collection(self, source: BaseMappedUrlSource) -> ResultSet | None:
        self._logger.info(f"Processing Issue / Collection {source.url}")

        try:
            scraper = self._scrape_url(source.url)

            # Find all PDF links using appropriate class or tag (if lambda returns True, it will be included in the list)
            html_tag_list = scraper.find_all(
                "a",
                href=lambda href: href and "#" not in href,
                class_=lambda class_: class_ and "reference" in class_ and "internal" in class_
            )

            self._logger.info(f"HTML links found: {len(html_tag_list)}")
            return html_tag_list
        except Exception as e:
            self._logger.error(f"Failed to process Issue / Collection {source.url}. Error: {e}")
            return None

    def _scrape_article(self, source: BaseMappedUrlSource) -> Tag | None:
        pass


class WikipediaScraper(BaseUrlPublisherScraper, BaseMappedScraper):
    def _scrape_journal(self, source: BaseMappedUrlSource) -> ResultSet | List[Tag] | None:
        pass

    def _scrape_issue_or_collection(self, source: BaseMappedUrlSource) -> List[Tag] | None:
        self._logger.info(f"Processing Issue / Collection {source.url}")

        try:
            self._scrape_url(source.url)

            html_tag_list = self._driver.find_elements(By.CSS_SELECTOR, "div.mw-category-generated a")

            self._logger.info(f"HTML links found: {len(html_tag_list)}")
            return [Tag(name="a", attrs={"href": tag.get("href")}) for tag in html_tag_list]
        except Exception as e:
            self._logger.error(f"Failed to process Issue / Collection {source.url}. Error: {e}")
            return None

    def _scrape_article(self, source: BaseMappedUrlSource) -> Tag | None:
        pass


class MITScraper(BaseUrlPublisherScraper, BaseMappedScraper):
    def _scrape_journal(self, source: BaseMappedUrlSource) -> ResultSet | List[Tag] | None:
        pass

    def _scrape_issue_or_collection(self, source: BaseMappedUrlSource) -> List[Tag] | None:
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

            self._logger.info(f"PDF links found: {len(pdf_tag_list)}")
            return pdf_tag_list
        except Exception as e:
            self._logger.error(f"Failed to process Issue / Collection {source.url}. Error: {e}")
            return None

    def _scrape_article(self, source: BaseMappedUrlSource) -> Tag | None:
        pass
