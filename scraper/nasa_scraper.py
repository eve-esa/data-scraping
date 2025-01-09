import random
import time
from typing import List, Type, Dict
from bs4 import Tag, ResultSet, BeautifulSoup

from helper.utils import get_scraped_url
from model.base_mapped_models import BaseMappedUrlSource, BaseMappedConfig
from model.base_models import BaseConfig
from model.base_pagination_publisher_models import BasePaginationPublisherScrapeOutput, BasePaginationPublisherConfig
from model.nasa_models import NASANTRSConfig
from scraper.base_pagination_publisher_scraper import BasePaginationPublisherScraper
from scraper.base_scraper import BaseScraper, BaseMappedScraper
from scraper.base_url_publisher_scraper import BaseUrlPublisherScraper
from service.adapter import ScrapeAdapter


class NASAScraper(BaseScraper):
    def __init__(self):
        super().__init__()

        self.__file_extensions = {}

    @property
    def config_model_type(self) -> Type[BaseMappedConfig]:
        """
        Return the configuration model type.

        Returns:
            Type[BaseMappedConfig]: The configuration model type
        """
        return BaseMappedConfig

    def scrape(self, model: BaseMappedConfig) -> Dict[str, List]:
        """
        Scrape the resources links.

        Args:
            model (BaseMappedConfig): The configuration model.

        Returns:
            Dict[str, List]: The output of the scraping.
        """
        pdf_links = {}
        mapping = {
            "NasaWikiScraper": NASAWikiScraper,
            "NasaNTRSScraper": NASANTRSScraper,
            "NasaEOSScraper": NASAEOSScraper,
        }
        for source in model.sources:
            self._logger.info(f"Processing source {source.name}")

            results = ScrapeAdapter(source.config, mapping.get(source.scraper)).scrape()
            if results is not None:
                pdf_links[source.name] = results
                self.__file_extensions[source.name] = source.config.file_extension

        return pdf_links

    def post_process(self, scrape_output: Dict[str, List]) -> Dict[str, List[str]]:
        """
        Post-process the scraped output. This method is called after the sources have been scraped. It is used to
        retrieve the final list of processed URLs. This method must be implemented in the derived class.

        Args:
            scrape_output (Dict[str, List]): The scraped output

        Returns:
            Dict[str, List[str]]: The results of the scraping
        """
        return scrape_output

    def _upload_to_s3(self, sources_links: Dict[str, List[str]]) -> bool:
        """
        Upload the source files to S3.

        Args:
            sources_links (Dict[str, List[str]]): The list of links of the various sources.

        Returns:
            bool: True if the upload was successful, False otherwise.
        """
        self._logger.info("Uploading files to S3")

        all_done = True
        for source_name, source_links in sources_links.items():
            file_extension = self.__file_extensions[source_name]

            for link in source_links:
                result = self._s3_client.upload(self.bucket_key, link, file_extension)
                if not result:
                    all_done = False

                # Sleep after each successful download to avoid overwhelming the server
                time.sleep(random.uniform(2, 5))

        return all_done


class NASAWikiScraper(BaseUrlPublisherScraper, BaseMappedScraper):
    def _scrape_journal(self, source: BaseMappedUrlSource) -> ResultSet | List[Tag] | None:
        pass

    def _scrape_issue_or_collection(self, source: BaseMappedUrlSource) -> ResultSet | List[Tag] | None:
        self._logger.info(f"Processing Issue / Collection {source.url}")

        try:
            driver = self._scrape_url(source.url)

            all_expanded = False
            while not all_expanded:
                all_expanded = driver.execute_script("""
                    toggles = document.querySelectorAll("a.aui-iconfont-chevron-right")
                    if (toggles.length == 0) {
                        return true;
                    }
                    toggles.forEach(toggle => {
                        toggle.click();
                        setTimeout(() => {}, 1000);
                    });
                    return false;
                """)

            scraper = BeautifulSoup(driver.page_source, "html.parser")

            html_tag_list = scraper.find_all(
                "a", href=lambda href: href and ("/display/" in href or "/pages/" in href) and "#" not in href
            )
            self._logger.info(f"HTML links found: {len(html_tag_list)}")

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
    def config_model_type(self) -> Type[NASANTRSConfig]:
        return NASANTRSConfig

    def scrape(self, model: NASANTRSConfig) -> BasePaginationPublisherScrapeOutput | None:
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
            scraper = BeautifulSoup(self._scrape_url(url).page_source, "html.parser")

            # Now, visit each article link and find the PDF link
            pdf_tag_list = scraper.find_all("a", href=lambda href: href and ".pdf" in href)

            self._logger.info(f"PDF links found: {len(pdf_tag_list)}")
            return pdf_tag_list
        except Exception as e:
            self._logger.error(f"Failed to process URL {url}. Error: {e}")
            return None


class NASAEOSScraper(BasePaginationPublisherScraper, BaseMappedScraper):
    @property
    def config_model_type(self) -> Type[BasePaginationPublisherConfig]:
        return BasePaginationPublisherConfig

    def scrape(self, model: BaseConfig) -> BasePaginationPublisherScrapeOutput | None:
        pdf_tags = []
        for idx, source in enumerate(model.sources):
            pdf_tags.extend(self._scrape_landing_page(source.landing_page_url, idx + 1))

        return {"NASA EOS": [get_scraped_url(tag, self.base_url) for tag in pdf_tags]} if pdf_tags else None

    def _scrape_landing_page(self, landing_page_url: str, source_number: int) -> ResultSet | List[Tag] | None:
        self._logger.info(f"Processing Landing Page {landing_page_url}")

        return self._scrape_pagination(landing_page_url, source_number, base_zero=True)

    def _scrape_page(self, url: str) -> ResultSet | List[Tag] | None:
        try:
            scraper = BeautifulSoup(self._scrape_url(url).page_source, "html.parser")

            # Now, visit each article link and find the PDF link
            pdf_tag_list = scraper.find_all("a", href=lambda href: href and ".pdf" in href)

            self._logger.info(f"PDF links found: {len(pdf_tag_list)}")
            return pdf_tag_list
        except Exception as e:
            self._logger.error(f"Failed to process URL {url}. Error: {e}")
            return None
