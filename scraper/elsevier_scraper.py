import os.path
import random
import shutil
import time
from typing import Type, List
from seleniumbase import SB

from helper.utils import get_scraped_url_by_bs_tag, get_sb_configuration
from model.elsevier_models import (
    SourceType,
    ElsevierConfig,
    ElsevierScraperOutput,
    ElsevierSource,
    ElsevierScrapeIssueOutput,
)
from scraper.base_scraper import BaseScraper


class ElsevierScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.__download_folder_path = None

    @property
    def config_model_type(self) -> Type[ElsevierConfig]:
        return ElsevierConfig

    def scrape(self) -> ElsevierScraperOutput | None:
        """
        Scrape the Elsevier website for the PDF links.

        Returns:
            ElsevierScraperOutput | None: The PDF links scraped from the website.
        """
        pdf_links = {}
        for source in self._config_model.sources:
            if source.type == SourceType.JOURNAL:
                links = self.__scrape_journal(source)
            else:
                result = self.__scrape_issue(source)
                links = result.pdf_links if result.pdf_links else None

            if links is not None:
                pdf_links[source.name] = links

        return pdf_links if pdf_links else None

    def post_process(self, scrape_output: ElsevierScraperOutput) -> List[str]:
        return [link for links in scrape_output.values() for link in links]

    def __scrape_journal(self, source: ElsevierSource) -> List[str] | None:
        """
        Scrape the journal for the issues. The logic is as follows:
        - Get the first issue link from the journal page, i.e., the newest issue.
        - Scrape the issue and get the next issue URL. If the issue was scraped successfully, add the issue URL to the
            list of journal links.
        - Repeat the process until there are no more issues to scrape.

        Args:
            source (ElsevierSource): The source model.

        Returns:
            List[str] | None: The list of journal links if the journal was scraped successfully, None otherwise
        """
        self._logger.info(f"Scraping Journal: {source.name}")

        try:
            scraper = self._scrape_url(source.url)

            # get the first link (i.e., the newest issue) in the page with the tag "a", class "js-issue-item-link"
            first_issue_tag = scraper.find("a", class_="js-issue-item-link")
            if first_issue_tag is None:
                self._log_and_save_failure(source.url, "No issue found")
                return None

            issue_url = get_scraped_url_by_bs_tag(first_issue_tag, self._config_model.base_url)

            journal_links = []
            while issue_url:
                # scrape the issue and get the next issue URL
                # (the latter can be None, if there are no more issues, so that the loop stops)
                result = self.__scrape_issue(
                    ElsevierSource(url=issue_url, name=source.name, type=str(SourceType.ISSUE))
                )
                if result.pdf_links:
                    journal_links.extend(result.pdf_links)
                issue_url = result.next_issue_url

            self._logger.info(f"Journal {source.name} scraped")
            return journal_links
        except Exception as e:
            self._log_and_save_failure(source.url, f"Error scraping journal: {e}")
            return None

    def __scrape_issue(self, source: ElsevierSource) -> ElsevierScrapeIssueOutput:
        """
        Scrape the issue for the PDFs. The logic is as follows:
        - Find the next issue URL, i.e., the URL of the previous issue, if it exists.
        - Check if there are any PDFs to download. If not, try with the next issue.
        - Download the PDFs in a zip file and wait for the download to complete.
        - Unpack the zip files in a temporary folder.
        - Return the result of the scraping. If the issue was scraped successfully, return the next issue URL, i.e.,
            the URL of the previous issue to scrape next.

        Args:
            source (ElsevierSource): The source model.

        Returns:
            ElsevierScrapeIssueOutput: The result of the scraping.
        """
        self._logger.info(f"Scraping Issue: {source.name}, URL: {source.url}")

        try:
            scraper = self._scrape_url(source.url)

            # find the element with tag "a", class "anchor" and attribute `navname` equal to "prev-next-issue"
            next_issue_tag = scraper.find("a", class_="anchor", navname="prev-next-issue")
            next_issue_link = get_scraped_url_by_bs_tag(
                next_issue_tag, self._config_model.base_url
            ) if next_issue_tag.get("href") else None

            # check for the presence of tags "a", class "pdf-download" with attribute `href` containing ".pdf"
            pdf_tags = scraper.find_all(
                "a",
                class_=lambda class_: class_ and "pdf-download" in class_,
                href=lambda href: href and ".pdf" in href
            )
            # if no PDF tag exists, try with the next issue since no PDF can be downloaded from the current one
            if not pdf_tags:
                self._save_failure(source.url)

            self._logger.debug(f"PDF links found: {len(pdf_tags)}")
            return ElsevierScrapeIssueOutput(
                pdf_links=[get_scraped_url_by_bs_tag(
                    tag, self._config_model.base_url, with_querystring=True
                ) for tag in pdf_tags],
                next_issue_url=next_issue_link
            )
        except Exception as e:
            self._log_and_save_failure(source.url, f"Error scraping issue: {e}")
            return ElsevierScrapeIssueOutput(next_issue_url=None)

    def upload_to_s3(self, sources_links: List[str]):
        def get_pid(link_: str) -> str:
            # from the `link`, get the `pid` parameter of the querystring
            try:
                pid = link_.split("pid=")[1].split("&")[0]
            except Exception:
                pid = None
            return pid

        self._logger.debug("Uploading files to S3")

        sb_configuration = get_sb_configuration()
        sb_configuration["external_pdf"] = True

        try:
            with SB(**sb_configuration) as driver:
                self.set_driver(driver)
                self._driver.activate_cdp_mode()
                self._driver.cdp.maximize()

                for link in sources_links:
                    if not (pid := get_pid(link)):
                        continue

                    # visit the PDF link
                    self._scrape_url(link)

                    if (file_path := self.__wait_end_download(pid)) is None:
                        continue

                    current_resource = self._uploaded_resource_repository.get_by_content(
                        self._logging_db_scraper, self._config_model.bucket_key, file_path
                    )
                    self._upload_resource_to_s3(current_resource, pid)

                    # remove the file and sleep after each successful upload to avoid overwhelming the server
                    os.remove(file_path)
                    time.sleep(random.uniform(2, 5))
        finally:
            shutil.rmtree(self.download_folder_path)

    def __wait_end_download(self, filename: str, timeout: int | None = 30, interval: float | None = 0.5) -> str | None:
        """
        Wait for the download to finish. If the download is not completed within the specified timeout, raise an
        exception.

        Args:
            filename (str): The name of the file to wait for.
            timeout (int): The timeout in seconds. Default is 10 seconds.
            interval (float): The interval in seconds to check for the file. Default is 0.5 seconds.
        """
        start_time = time.time()
        download_folder_path = self._driver.get_browser_downloads_folder()

        # wait until the download is completed
        while time.time() - start_time < timeout:
            time.sleep(interval)
            completed_downloads = sorted(
                [f for f in os.listdir(download_folder_path) if filename in f],
                key=lambda x: os.path.getmtime(os.path.join(download_folder_path, x)),
                reverse=True
            )
            if not completed_downloads:
                continue

            # move the downloaded file to the download folder
            file = completed_downloads[0]
            new_path = os.path.join(self.download_folder_path, file)
            os.replace(os.path.join(download_folder_path, file), new_path)
            return new_path

        return None

    @property
    def download_folder_path(self) -> str:
        if self.__download_folder_path is None:
            download_folder_path = os.path.join(self._driver.get_browser_downloads_folder(), "elsevier")
            os.makedirs(download_folder_path, exist_ok=True)

            self.__download_folder_path = download_folder_path

        return self.__download_folder_path
