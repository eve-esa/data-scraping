import os.path
import random
import time
from typing import Type, List

from helper.utils import get_scraped_url_by_bs_tag, unpack_zip_files
from model.elsevier_models import (
    SourceType,
    ElsevierConfig,
    ElsevierScraperOutput,
    ElsevierSource,
    ElsevierScrapeIssueOutput,
)
from scraper.base_scraper import BaseScraper


class ElsevierScraper(BaseScraper):
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
                links = [source.url] if result.was_scraped else None

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
                if result.was_scraped:
                    journal_links.append(issue_url)
                issue_url = result.next_issue_url

            self._logger.info(f"Journal {source.name} scraped")

            if not journal_links:
                self._save_failure(source.url)
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
                self._log_and_save_failure(source.url, f"No downloadable PDF found at the URL: {source.url}")
                return ElsevierScrapeIssueOutput(was_scraped=False, next_issue_url=next_issue_link)

            # wait for the page to load and get the element with tag "button", child of "form.js-download-full-issue-form"
            # click on the button to download the issue
            self._driver.cdp.click("form.js-download-full-issue-form button", timeout=10)

            # wait for the download to complete
            download_folder_path = self._driver.get_browser_downloads_folder()
            self._logger.info(f"Downloading PDFs from {source.url} to {download_folder_path}")
            self.__wait_end_download()

            self._driver.delete_all_cookies()

            # unpack zip files before uploading
            if not unpack_zip_files(download_folder_path):
                self._logger.warning("No zip files found or timeout reached")
                return ElsevierScrapeIssueOutput(was_scraped=False, next_issue_url=next_issue_link)

            return ElsevierScrapeIssueOutput(was_scraped=True, next_issue_url=next_issue_link)
        except Exception as e:
            self._log_and_save_failure(source.url, f"Error scraping issue: {e}")
            return ElsevierScrapeIssueOutput(was_scraped=False, next_issue_url=None)

    def __wait_end_download(self, timeout: int | None = 60):
        """
        Wait for the download to finish. If the download is not completed within the specified timeout, raise an
        exception.

        Args:
            timeout (int): The timeout in seconds. Default is 60 seconds.
        """
        start_time = time.time()
        download_folder_path = self._driver.get_browser_downloads_folder()

        # first of all, wait until the `js-pdf-download-modal-content` element is no more present
        self._driver.cdp.assert_element_absent("div.js-pdf-download-modal-content", timeout=timeout)

        # then, wait until the download is completed
        while time.time() - start_time < timeout:
            # check if there are completed zip files temporary files in the directory
            completed_downloads = [f for f in os.listdir(download_folder_path) if f.endswith(".zip")]
            if completed_downloads:
                return

            time.sleep(0.1)

    def upload_to_s3(self, sources_links: List[str]):
        self._logger.debug("Uploading files to S3")

        download_folder_path = self._driver.get_browser_downloads_folder()

        for file in os.listdir(download_folder_path):
            if not file.endswith(self._config_model.file_extension):
                continue

            file_path = self._driver.get_path_of_downloaded_file(file)
            if not os.path.isfile(file_path):
                continue

            current_resource = self._uploaded_resource_repository.get_by_content(
                self._logging_db_scraper, self._config_model.bucket_key, file_path
            )
            self._upload_resource_to_s3(current_resource, file)

            # Sleep after each successful upload to avoid overwhelming the server
            time.sleep(random.uniform(2, 5))
