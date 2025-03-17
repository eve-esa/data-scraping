import random
from typing import List, Type, Dict
from bs4 import Tag, ResultSet

from helper.utils import get_scraped_url_by_bs_tag
from model.base_mapped_models import BaseMappedUrlSource, BaseMappedPaginationConfig, BaseMappedCrawlingConfig
from model.base_pagination_publisher_models import BasePaginationPublisherScrapeOutput
from model.base_url_publisher_models import BaseUrlPublisherConfig
from model.nasa_models import NASANTRSConfig, NASANTRSScraperOutput
from model.sql_models import ScraperFailure
from scraper.base_crawling_scraper import BaseCrawlingScraper
from scraper.base_mapped_publisher_scraper import BaseMappedPublisherScraper
from scraper.base_pagination_publisher_scraper import BasePaginationPublisherScraper
from scraper.base_scraper import BaseMappedSubScraper, BaseScraper
from scraper.base_url_publisher_scraper import BaseUrlPublisherScraper


class NASAScraper(BaseMappedPublisherScraper):
    @property
    def mapping(self) -> Dict[str, Type[BaseMappedSubScraper]]:
        return {
            "NASAEarthDataWikiScraper": NASAEarthDataWikiScraper,
            "NASANTRSScraper": NASANTRSScraper,
            "NASAEOSScraper": NASAEOSScraper,
            "NASAEarthDataScraper": NASAEarthDataScraper,
            "NASAEarthDataPDFScraper": NASAEarthDataPDFScraper,
            "NASACrawlingScraper": NASACrawlingScraper,
        }


class NASAEarthDataWikiScraper(BaseUrlPublisherScraper, BaseMappedSubScraper):
    @property
    def config_model_type(self) -> Type[BaseUrlPublisherConfig]:
        """
        Return the configuration model type.

        Returns:
            Type[BaseUrlPublisherConfig]: The configuration model type
        """
        return BaseUrlPublisherConfig

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

            if not (html_tag_list := self._get_parsed_page_source().find_all(
                "a", href=lambda href: href and ("/display/" in href or "/pages/" in href) and "#" not in href
            )):
                self._save_failure(source.url)

            self._logger.debug(f"HTML links found: {len(html_tag_list)}")
            return html_tag_list
        except Exception as e:
            self._log_and_save_failure(source.url, f"Failed to process Issue / Collection {source.url}. Error: {e}")
            return None

    def _scrape_article(self, source: BaseMappedUrlSource) -> Tag | None:
        pass


class NASANTRSScraper(BaseMappedSubScraper, BaseScraper):
    @property
    def config_model_type(self) -> Type[NASANTRSConfig]:
        return NASANTRSConfig

    def scrape(self) -> NASANTRSScraperOutput | None:
        pdf_tags = []
        for idx, source in enumerate(self._config_model.sources):
            self._logger.info(f"Processing Source {source.url}")

            scraper = self._scrape_url(source.url)
            while True:
                if not (pdf_tag_list := scraper.find_all("a", href=lambda href: href and ".pdf" in href)):
                    self._logger.info("No PDF links found: Breaking the loop")
                    break

                self._logger.debug(f"PDF links found: {len(pdf_tag_list)}")

                pdf_tags.extend(pdf_tag_list)

                try:
                    next_page_button = self._driver.cdp.find_element("button.mat-paginator-navigation-next")

                    # if next page button has class `mat-button-disabled`, then break the loop
                    if "mat-button-disabled" in next_page_button.get_attribute("class"):
                        break

                    # otherwise, click on it and wait until the page is loaded
                    self._logger.info("Clicking on Next Page Button")
                    self._driver.execute_script("arguments[0].click();", next_page_button)

                    # Sleep for some time to avoid being blocked by the server on the next request
                    self._driver.cdp.sleep(random.uniform(2, 5))

                    self._driver.uc_gui_click_captcha()
                    self._wait_for_page_load()
                    self._handle_cookie()

                    scraper = self._get_parsed_page_source()
                except:
                    break

        return {"NASA NTRS": [
            get_scraped_url_by_bs_tag(tag, self._config_model.base_url) for tag in pdf_tags
        ]} if pdf_tags else None

    def scrape_link(self, failure: ScraperFailure) -> List[str]:
        link = failure.source
        self._logger.info(f"Scraping URL: {link}")

        scraper = self._scrape_url(link)
        pdf_tags = scraper.find_all("a", href=lambda href: href and ".pdf" in href)

        return [get_scraped_url_by_bs_tag(tag, self._config_model.base_url) for tag in pdf_tags]

    def post_process(self, scrape_output: NASANTRSScraperOutput) -> List[str]:
        return [link for links in scrape_output.values() for link in links]


class NASAEOSScraper(BasePaginationPublisherScraper, BaseMappedSubScraper):
    @property
    def config_model_type(self) -> Type[BaseMappedPaginationConfig]:
        return BaseMappedPaginationConfig

    def scrape(self) -> BasePaginationPublisherScrapeOutput | None:
        pdf_tags = []
        for idx, source in enumerate(self._config_model.sources):
            pdf_tags.extend(self._scrape_landing_page(source.landing_page_url, idx + 1))

        return {"NASA EOS": [
            get_scraped_url_by_bs_tag(tag, self._config_model.base_url) for tag in pdf_tags
        ]} if pdf_tags else None

    def _scrape_landing_page(self, landing_page_url: str, source_number: int) -> List[Tag]:
        self._logger.info(f"Processing Landing Page {landing_page_url}")

        return self._scrape_pagination(landing_page_url, source_number, base_zero=True)

    def _scrape_page(self, url: str) -> ResultSet | List[Tag] | None:
        try:
            scraper = self._scrape_url(url)

            if not (pdf_tag_list := scraper.find_all("a", href=lambda href: href and ".pdf" in href)):
                self._save_failure(url)

            self._logger.debug(f"PDF links found: {len(pdf_tag_list)}")
            return pdf_tag_list
        except Exception as e:
            self._log_and_save_failure(url, f"Failed to process URL {url}. Error: {e}")
            return None


class NASAEarthDataScraper(BasePaginationPublisherScraper, BaseMappedSubScraper):
    def __init__(self):
        super().__init__()
        self.__href = None

    @property
    def config_model_type(self) -> Type[BaseMappedPaginationConfig]:
        return BaseMappedPaginationConfig

    def scrape(self) -> BasePaginationPublisherScrapeOutput | None:
        html_tags = []
        for idx, source in enumerate(self._config_model.sources):
            self.__href = source.href
            html_tags.extend(self._scrape_landing_page(source.landing_page_url, idx + 1))

        return {"NASA EarthData": [
            get_scraped_url_by_bs_tag(tag, self._config_model.base_url) for tag in html_tags
        ]} if html_tags else None

    def _scrape_landing_page(self, landing_page_url: str, source_number: int) -> ResultSet | List[Tag] | None:
        self._logger.info(f"Processing Landing Page {landing_page_url}")

        return self._scrape_pagination(landing_page_url, source_number, base_zero=True)

    def _scrape_page(self, url: str) -> ResultSet | List[Tag] | None:
        try:
            scraper = self._scrape_url(url)

            if not (html_tag_list := scraper.find_all("a", href=lambda href: href and self.__href in href, hreflang="en")):
                self._save_failure(url)

            self._logger.debug(f"HTML links found: {len(html_tag_list)}")
            return html_tag_list
        except Exception as e:
            self._log_and_save_failure(url, f"Failed to process URL {url}. Error: {e}")
            return None


class NASAEarthDataPDFScraper(NASAEarthDataScraper):
    def scrape(self) -> BasePaginationPublisherScrapeOutput | None:
        pdf_tags = []
        for idx, source in enumerate(self._config_model.sources):
            self.__href = source.href
            pdf_tags.extend(self._scrape_landing_page(source.landing_page_url, idx + 1))

        return {"NASA EarthData PDF": [
            get_scraped_url_by_bs_tag(tag, self._config_model.base_url) for tag in pdf_tags
        ]} if pdf_tags else None

    def _scrape_page(self, url: str) -> ResultSet | List[Tag] | None:
        try:
            scraper = self._scrape_url(url)

            html_links = [
                get_scraped_url_by_bs_tag(tag, self._config_model.base_url)
                for tag in scraper.find_all("a", href=lambda href: href and self.__href in href, hreflang="en")
            ]

            pdf_tag_list = []
            for html_link in html_links:
                self._logger.info(f"Processing URL {html_link}")
                self._driver.cdp.open(html_link)
                self._driver.cdp.sleep(1)

                pdf_tag_list.extend(self._get_parsed_page_source().find_all(
                    "a", href=lambda href: href and ".pdf" in href, hreflang="en"
                ))

            self._logger.debug(f"PDF links found: {len(pdf_tag_list)}")

            if not pdf_tag_list:
                self._save_failure(url)
            return pdf_tag_list
        except Exception as e:
            self._log_and_save_failure(url, f"Failed to process URL {url}. Error: {e}")
            return None


class NASACrawlingScraper(BaseCrawlingScraper, BaseMappedSubScraper):
    @property
    def config_model_type(self) -> Type[BaseMappedCrawlingConfig]:
        return BaseMappedCrawlingConfig

    @property
    def crawling_folder_path(self) -> str:
        return "nasa"
