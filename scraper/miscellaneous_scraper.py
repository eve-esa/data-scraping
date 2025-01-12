from typing import List, Dict, Type
from bs4 import ResultSet, Tag
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
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
            "MITScraper": MITScraper,
            "JAXAScraper": JAXAScraper,
            "UKMetOfficeScraper": UKMetOfficeScraper,
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


class JAXAScraper(BaseUrlPublisherScraper, BaseMappedScraper):
    def _scrape_journal(self, source: BaseMappedUrlSource) -> ResultSet | List[Tag] | None:
        pass

    def _scrape_issue_or_collection(self, source: BaseMappedUrlSource) -> ResultSet | None:
        self._logger.info(f"Processing Issue / Collection {source.url}")

        try:
            scraper = self._scrape_url(source.url)

            # Find all PDF links using appropriate class or tag (if lambda returns True, it will be included in the list)
            html_tag_list = scraper.find_all("a", href=True, class_="btn--outline")

            self._logger.info(f"HTML links found: {len(html_tag_list)}")
            return html_tag_list
        except Exception as e:
            self._logger.error(f"Failed to process Issue / Collection {source.url}. Error: {e}")
            return None

    def _scrape_article(self, source: BaseMappedUrlSource) -> Tag | None:
        pass


class UKMetOfficeScraper(BaseUrlPublisherScraper, BaseMappedScraper):
    def _scrape_journal(self, source: BaseMappedUrlSource) -> ResultSet | List[Tag] | None:
        pass

    def _scrape_issue_or_collection(self, source: BaseMappedUrlSource) -> List[Tag] | None:
        self._logger.info(f"Processing Issue / Collection {source.url}")

        try:
            self._scrape_url(source.url)

            pdf_tag_list = []

            page_buttons = self._driver.find_elements(By.CSS_SELECTOR, "a.role-button.page-link")
            for page_button in page_buttons:
                page_button.click()
                self.__wait_for_loader_hidden()

                scraper = self._get_parsed_page_source()
                pdf_tag_list.extend(scraper.find_all("a", href=True, class_="card-link-value"))

            self._logger.info(f"PDF links found: {len(pdf_tag_list)}")
            return pdf_tag_list
        except Exception as e:
            self._logger.error(f"Failed to process Issue / Collection {source.url}. Error: {e}")
            return None

    def _scrape_article(self, source: BaseMappedUrlSource) -> Tag | None:
        pass

    def __wait_for_loader_hidden(self, timeout: int | None = 10) -> bool:
        """
        Using self._driver, wait until the parent of the parent of div.loader-admin has style display: none

        Args:
            timeout (int | None): The maximum time to wait for the loader to be hidden

        Returns:
            bool: True if the loader is hidden, False otherwise
        """

        try:
            loader = self._driver.find_element(By.ID, "loading-overflow")

            WebDriverWait(self._driver, timeout).until(
                lambda x: "display: none" in loader.get_attribute("style")
            )
            return True
        except:
            return False
