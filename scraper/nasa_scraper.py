import os
from typing import List, Type, Dict
from bs4 import Tag, ResultSet

from helper.utils import get_scraped_url
from model.base_mapped_models import BaseMappedUrlSource, BaseMappedPaginationConfig, BaseMappedCrawlingConfig
from model.base_pagination_publisher_models import BasePaginationPublisherScrapeOutput
from scraper.base_crawling_scraper import BaseCrawlingScraper
from scraper.base_mapped_publisher_scraper import BaseMappedPublisherScraper
from scraper.base_pagination_publisher_scraper import BasePaginationPublisherScraper
from scraper.base_scraper import BaseMappedScraper
from scraper.base_url_publisher_scraper import BaseUrlPublisherScraper


class NASAScraper(BaseMappedPublisherScraper):
    @property
    def mapping(self) -> Dict[str, Type[BaseMappedScraper]]:
        return {
            "NASAEarthDataWikiScraper": NASAEarthDataWikiScraper,
            "NASANTRSScraper": NASANTRSScraper,
            "NASAEOSScraper": NASAEOSScraper,
            "NASAEarthDataScraper": NASAEarthDataScraper,
            "NASAEarthDataPDFScraper": NASAEarthDataPDFScraper,
            "NASACrawlingScraper": NASACrawlingScraper,
        }


class NASAEarthDataWikiScraper(BaseUrlPublisherScraper, BaseMappedScraper):
    def _scrape_journal(self, source: BaseMappedUrlSource) -> ResultSet | List[Tag] | None:
        pass

    def _scrape_issue_or_collection(self, source: BaseMappedUrlSource) -> ResultSet | List[Tag] | None:
        self._logger.info(f"Processing Issue / Collection {source.url}")

        try:
            self._scrape_url(source.url)

            all_expanded = False
            while not all_expanded:
                all_expanded = self._driver.execute_script("""
                    let expandAll = async () => {
                        let toggles = document.querySelectorAll("a.aui-iconfont-chevron-right");
                        if (toggles.length == 0) {
                            return true;
                        }
                        for (const toggle of toggles) {
                            toggle.click();
                            await new Promise(resolve => setTimeout(resolve, 1000));
                        }
                        return false;
                    }
                    return await expandAll();
                """)

            html_tag_list = self._get_parsed_page_source().find_all(
                "a", href=lambda href: href and ("/display/" in href or "/pages/" in href) and "#" not in href
            )
            self._logger.debug(f"HTML links found: {len(html_tag_list)}")

            return html_tag_list
        except Exception as e:
            self._logger.error(f"Failed to process Issue / Collection {source.url}. Error: {e}")
            return None

    def _scrape_article(self, source: BaseMappedUrlSource) -> Tag | None:
        pass


class NASANTRSScraper(BasePaginationPublisherScraper, BaseMappedScraper):
    def __init__(self):
        super().__init__()
        self.__page_size = None

    @property
    def config_model_type(self) -> Type[BaseMappedPaginationConfig]:
        return BaseMappedPaginationConfig

    def scrape(self, model: BaseMappedPaginationConfig) -> BasePaginationPublisherScrapeOutput | None:
        pdf_tags = []
        for idx, source in enumerate(model.sources):
            self.__page_size = source.page_size
            pdf_tags.extend(self._scrape_landing_page(source.landing_page_url, idx + 1))

        return {"NASA NTRS": [get_scraped_url(tag, self.base_url) for tag in pdf_tags]} if pdf_tags else None

    def _scrape_landing_page(self, landing_page_url: str, source_number: int) -> ResultSet | List[Tag] | None:
        self._logger.info(f"Processing Landing Page {landing_page_url}")

        return self._scrape_pagination(landing_page_url, source_number, base_zero=True, page_size=self.__page_size)

    def _scrape_page(self, url: str) -> ResultSet | List[Tag] | None:
        try:
            scraper = self._scrape_url(url)

            # Now, visit each article link and find the PDF link
            pdf_tag_list = scraper.find_all("a", href=lambda href: href and ".pdf" in href)

            self._logger.debug(f"PDF links found: {len(pdf_tag_list)}")
            return pdf_tag_list
        except Exception as e:
            self._logger.error(f"Failed to process URL {url}. Error: {e}")
            return None


class NASAEOSScraper(BasePaginationPublisherScraper, BaseMappedScraper):
    @property
    def config_model_type(self) -> Type[BaseMappedPaginationConfig]:
        return BaseMappedPaginationConfig

    def scrape(self, model: BaseMappedPaginationConfig) -> BasePaginationPublisherScrapeOutput | None:
        pdf_tags = []
        for idx, source in enumerate(model.sources):
            pdf_tags.extend(self._scrape_landing_page(source.landing_page_url, idx + 1))

        return {"NASA EOS": [get_scraped_url(tag, self.base_url) for tag in pdf_tags]} if pdf_tags else None

    def _scrape_landing_page(self, landing_page_url: str, source_number: int) -> ResultSet | List[Tag] | None:
        self._logger.info(f"Processing Landing Page {landing_page_url}")

        return self._scrape_pagination(landing_page_url, source_number, base_zero=True)

    def _scrape_page(self, url: str) -> ResultSet | List[Tag] | None:
        try:
            scraper = self._scrape_url(url)

            pdf_tag_list = scraper.find_all("a", href=lambda href: href and ".pdf" in href)

            self._logger.debug(f"PDF links found: {len(pdf_tag_list)}")
            return pdf_tag_list
        except Exception as e:
            self._logger.error(f"Failed to process URL {url}. Error: {e}")
            return None


class NASAEarthDataScraper(BasePaginationPublisherScraper, BaseMappedScraper):
    def __init__(self):
        super().__init__()
        self.__href = None

    @property
    def config_model_type(self) -> Type[BaseMappedPaginationConfig]:
        return BaseMappedPaginationConfig

    def scrape(self, model: BaseMappedPaginationConfig) -> BasePaginationPublisherScrapeOutput | None:
        html_tags = []
        for idx, source in enumerate(model.sources):
            self.__href = source.href
            html_tags.extend(self._scrape_landing_page(source.landing_page_url, idx + 1))

        return {"NASA EarthData": [get_scraped_url(tag, self.base_url) for tag in html_tags]} if html_tags else None

    def _scrape_landing_page(self, landing_page_url: str, source_number: int) -> ResultSet | List[Tag] | None:
        self._logger.info(f"Processing Landing Page {landing_page_url}")

        return self._scrape_pagination(landing_page_url, source_number, base_zero=True)

    def _scrape_page(self, url: str) -> ResultSet | List[Tag] | None:
        try:
            scraper = self._scrape_url(url)

            html_tag_list = scraper.find_all("a", href=lambda href: href and self.__href in href, hreflang="en")

            self._logger.debug(f"HTML links found: {len(html_tag_list)}")
            return html_tag_list
        except Exception as e:
            self._logger.error(f"Failed to process URL {url}. Error: {e}")
            return None


class NASAEarthDataPDFScraper(NASAEarthDataScraper):
    def scrape(self, model: BaseMappedPaginationConfig) -> BasePaginationPublisherScrapeOutput | None:
        pdf_tags = []
        for idx, source in enumerate(model.sources):
            self.__href = source.href
            pdf_tags.extend(self._scrape_landing_page(source.landing_page_url, idx + 1))

        return {"NASA EarthData PDF": [get_scraped_url(tag, self.base_url) for tag in pdf_tags]} if pdf_tags else None

    def _scrape_page(self, url: str) -> ResultSet | List[Tag] | None:
        try:
            scraper = self._scrape_url(url)

            html_links = [
                get_scraped_url(tag, self.base_url)
                for tag in scraper.find_all("a", href=lambda href: href and self.__href in href, hreflang="en")
            ]

            pdf_tag_list = []
            for html_link in html_links:
                self._logger.info(f"Processing URL {html_link}")

                pdf_tag_list.extend(self._scrape_url(html_link).find_all(
                    "a", href=lambda href: href and ".pdf" in href, hreflang="en"
                ))

            self._logger.debug(f"PDF links found: {len(pdf_tag_list)}")
            return pdf_tag_list
        except Exception as e:
            self._logger.error(f"Failed to process URL {url}. Error: {e}")
            return None


class NASACrawlingScraper(BaseCrawlingScraper, BaseMappedScraper):
    @property
    def config_model_type(self) -> Type[BaseMappedCrawlingConfig]:
        return BaseMappedCrawlingConfig

    @property
    def crawling_folder_path(self) -> str:
        return os.path.join(os.getcwd(), "crawled", "nasa")
