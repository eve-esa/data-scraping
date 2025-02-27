import os
import random
import shutil
import time
from typing import Type, Dict, List
from uuid import uuid4
from bs4 import ResultSet, Tag

from helper.utils import get_scraped_url_by_bs_tag, get_scraped_url_by_web_element
from model.base_iterative_publisher_models import IterativePublisherScrapeIssueOutput
from model.base_mapped_models import BaseMappedIterativeWithConstraintJournal, BaseMappedPaginationConfig
from model.base_pagination_publisher_models import BasePaginationPublisherScrapeOutput
from model.copernicus_models import CopernicusConfig
from scraper.base_iterative_publisher_scraper import BaseIterativeWithConstraintPublisherScraper
from scraper.base_mapped_publisher_scraper import BaseMappedPublisherScraper
from scraper.base_pagination_publisher_scraper import BasePaginationPublisherScraper
from scraper.base_scraper import BaseMappedSubScraper


class CopernicusScraper(BaseMappedPublisherScraper):
    @property
    def mapping(self) -> Dict[str, Type[BaseMappedSubScraper]]:
        return {
            "CopernicusEgupScraper": CopernicusEgupScraper,
            "CopernicusServiceCatalogueScraper": CopernicusServiceCatalogueScraper,
        }


class CopernicusEgupScraper(BaseIterativeWithConstraintPublisherScraper, BaseMappedSubScraper):
    @property
    def config_model_type(self) -> Type[CopernicusConfig]:
        """
        Return the configuration model type.

        Returns:
            Type[CopernicusConfig]: The configuration model type
        """
        return CopernicusConfig

    def journal_identifier(self, model: BaseMappedIterativeWithConstraintJournal) -> str:
        """
        Return the journal identifier.

        Args:
            model (BaseMappedIterativeWithConstraintJournal): The configuration model.

        Returns:
            str: The journal identifier
        """
        return model.name

    def _scrape_issue(
        self, journal: BaseMappedIterativeWithConstraintJournal, volume_num: int, issue_num: int
    ) -> IterativePublisherScrapeIssueOutput | None:
        """
        Scrape the issue URL for PDF links.

        Args:
            journal (BaseMappedIterativeWithConstraintJournal): The journal to scrape.
            volume_num (int): The volume number.
            issue_num (int): The issue number.

        Returns:
            IterativePublisherScrapeIssueOutput | None: A list of PDF links found in the issue, or None is something went wrong.
        """
        issue_url = os.path.join(journal.url, "articles", str(volume_num), f"issue{issue_num}.html")
        self._logger.info(f"Processing Issue URL: {issue_url}")

        try:
            scraper = self._scrape_url(issue_url)

            # find all the URLs to the articles where I can grab the PDF links (one per article URL, if lambda returns
            # True, it will be included in the list)
            tags = scraper.find_all("a", class_="article-title", href=lambda href: href and "/articles/" in href)

            if not (pdf_links := [
                pdf_link
                for pdf_link in map(
                    lambda tag: self._scrape_article(get_scraped_url_by_bs_tag(tag, journal.url), journal.url), tags
                )
                if pdf_link
            ]):
                self._save_failure(issue_url)

            self._logger.debug(f"PDF links found: {len(pdf_links)}")
            return pdf_links
        except Exception as e:
            self._log_and_save_failure(issue_url, f"Failed to process Issue {issue_num} in Volume {volume_num}. Error: {e}")
            return None

    def _scrape_article(self, article_url: str, base_url: str) -> str | None:
        """
        Scrape a single article.

        Args:
            article_url (str): The article links to scrape.
            base_url (str): The base URL.

        Returns:
            str | None: The string containing the PDF link.
        """
        self._logger.info(f"Processing Article URL: {article_url}")

        try:
            scraper = self._scrape_url(article_url)

            # Find all PDF links using appropriate class or tag (if lambda returns True, it will be included in the list)
            if pdf_tag := scraper.find("a", href=lambda href: href and ".pdf" in href):
                return get_scraped_url_by_bs_tag(pdf_tag, base_url)

            self._save_failure(article_url)
            return None
        except Exception as e:
            self._log_and_save_failure(article_url, f"Failed to process Article {article_url}. Error: {e}")
            return None


class CopernicusServiceCatalogueScraper(BasePaginationPublisherScraper, BaseMappedSubScraper):
    def __init__(self):
        super().__init__()
        self.__download_folder_path = None

    @property
    def config_model_type(self) -> Type[BaseMappedPaginationConfig]:
        return BaseMappedPaginationConfig

    def scrape(self) -> BasePaginationPublisherScrapeOutput | None:
        pdf_tags = []
        for idx, source in enumerate(self._config_model.sources):
            pdf_tags.extend(self._scrape_landing_page(source.landing_page_url, idx + 1))

        return {"Copernicus Service Catalogues": [
            get_scraped_url_by_bs_tag(tag, self._config_model.base_url) for tag in pdf_tags
        ]} if pdf_tags else None

    def _scrape_landing_page(self, landing_page_url: str, source_number: int) -> ResultSet | List[Tag] | None:
        self._logger.info(f"Processing Landing Page {landing_page_url}")

        return self._scrape_pagination(landing_page_url, source_number, base_zero=True)

    def _scrape_page(self, url: str) -> ResultSet | List[Tag] | None:
        try:
            self._scrape_url(url)
            if not (article_tags := self._driver.cdp.find_elements("div.service-catalogue-articles a")):
                self._save_failure(url)

            html_tag_list = []
            for article_tag in article_tags:
                # for each article, visit the URL and click on the "Read more" button if it exists
                article_url = get_scraped_url_by_web_element(article_tag, self._config_model.base_url)
                self._logger.info(f"Processing Catalogue URL: {article_url}")

                self._driver.cdp.open(article_url)
                self._driver.cdp.sleep(1)
                self._driver.cdp.click_if_visible("a.ec-toggle-link.ecf-open")

                # write the HTML source to a file
                with open(os.path.join(self.download_folder_path, f"{uuid4()}.html"), "w") as f:
                    f.write(self._driver.get_page_source())

                # now, check if there is a link to an external source within the article
                try:
                    external_url = get_scraped_url_by_web_element(
                        self._driver.cdp.find_element("a.btn-outline-primary"), self._config_model.base_url
                    )
                    # if the external URL is the same as the article URL, skip it
                    if external_url == article_url:
                        continue

                    self._logger.info(f"Processing Catalogues Source URL: {external_url}")

                    # visit the external URL and click on the buttons to see the full content of the page
                    self._driver.cdp.open(external_url)
                    self._driver.cdp.sleep(1)
                    self._driver.cdp.click_if_visible("button:contains('Accept all')")
                    self._driver.cdp.sleep(1)
                    self._driver.cdp.click_if_visible("button:contains('Overview')")
                    self._driver.cdp.sleep(1)
                    self._driver.cdp.click_if_visible("span:contains('Read more')")

                    # write the HTML source to a file
                    with open(os.path.join(self.download_folder_path, f"{uuid4()}.html"), "w") as f:
                        f.write(self._driver.get_page_source())

                    html_tag_list.append(Tag(name="a", attrs={"href": external_url}))
                except Exception:
                    pass

                html_tag_list.append(Tag(name="a", attrs={"href": article_url}))

            self._logger.debug(f"PDF links found: {len(html_tag_list)}")
            return html_tag_list
        except Exception as e:
            self._log_and_save_failure(url, f"Failed to process URL {url}. Error: {e}")
            return None

    def upload_to_s3(self, sources_links: List[str]):
        self._logger.debug("Uploading files to S3")
        download_folder = self.download_folder_path

        file_paths = [
            os.path.join(download_folder, file)
            for file in os.listdir(download_folder)
            if file.endswith(self._config_model.file_extension)
               and os.path.isfile(os.path.join(download_folder, file))
        ]
        if not file_paths:
            for source_link in sources_links:
                self._save_failure(source_link, f"No files found in the downloading folder: {source_link}")

        for file_path in file_paths:
            current_resource = self._uploaded_resource_repository.get_by_content(
                self._logging_db_scraper, self._config_model.bucket_key, file_path
            )
            self._upload_resource_to_s3(current_resource, file_path.replace(download_folder, ""))

            # Sleep after each successful upload to avoid overwhelming the server
            time.sleep(random.uniform(2, 5))

        shutil.rmtree(self.download_folder_path)

    @property
    def download_folder_path(self) -> str:
        if self.__download_folder_path is None:
            download_folder_path = os.path.join(self._driver.get_browser_downloads_folder(), "copernicus")
            os.makedirs(download_folder_path, exist_ok=True)

            self.__download_folder_path = download_folder_path

        return self.__download_folder_path
