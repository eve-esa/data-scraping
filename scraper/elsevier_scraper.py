import os.path
import random
import shutil
import time
from typing import Type, List
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from helper.utils import get_scraped_url, unpack_zip_files
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

        self._download_folder_path = os.path.join(os.getcwd(), "downloads")

    @property
    def config_model_type(self) -> Type[ElsevierConfig]:
        return ElsevierConfig

    def scrape(self, model: ElsevierConfig) -> ElsevierScraperOutput | None:
        """
        Scrape the Elsevier website for the PDF links.

        Args:
            model (ElsevierConfig): The Elsevier configuration model.

        Returns:
            ElsevierScraperOutput | None: The PDF links scraped from the website.
        """
        pdf_links = {}
        for source in model.sources:
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
                self._logger.error("No issue found")
                return None

            issue_url = get_scraped_url(first_issue_tag, self._config_model.base_url)

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
            return journal_links
        except Exception as e:
            self._logger.error(f"Error scraping journal: {e}")
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
            next_issue_link = get_scraped_url(next_issue_tag, self.base_url) if next_issue_tag.get("href") else None

            # check for the presence of tags "a", class "pdf-download" with attribute `href` containing ".pdf"
            pdf_tags = scraper.find_all(
                "a",
                class_=lambda class_: class_ and "pdf-download" in class_,
                href=lambda href: href and ".pdf" in href
            )
            # if no PDF tag exists, try with the next issue since no PDF can be downloaded from the current one
            if not pdf_tags:
                self._logger.error(f"No downloadable PDF found at the URL: {source.url}")
                return ElsevierScrapeIssueOutput(was_scraped=False, next_issue_url=next_issue_link)

            # wait for the page to load and get the element with tag "button", child of "form.js-download-full-issue-form"
            button_download = WebDriverWait(self._driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "form.js-download-full-issue-form button"))
            )
            # click on the button to download the issue
            self._driver.execute_script("arguments[0].click();", button_download)

            # wait for the download to complete
            self._logger.info(f"Downloading PDFs from {source.url}")
            self.__wait_end_download()

            # unpack zip files before uploading
            unpack_zip_files(self._download_folder_path)

            return ElsevierScrapeIssueOutput(was_scraped=True, next_issue_url=next_issue_link)
        except Exception as e:
            self._logger.error(f"Error scraping journal: {e}")
            return ElsevierScrapeIssueOutput(was_scraped=False, next_issue_url=None)

    def __wait_end_download(self, timeout: int | None = 60):
        """
        Wait for the download to finish. If the download is not completed within the specified timeout, raise an
        exception.

        Args:
            timeout (int): The timeout in seconds. Default is 60 seconds.
        """
        start_time = time.time()

        while time.time() - start_time < timeout:
            # check if there are completed zip files temporary files in the directory
            completed_downloads = [f for f in os.listdir(self._download_folder_path) if f.endswith(".zip")]
            if completed_downloads:
                return

            time.sleep(0.1)

    def upload_to_s3(self, sources_links: List[str], **kwargs) -> bool:
        """
        Upload the source files to S3.

        Args:
            sources_links (List[str]): The list of links of the various sources.

        Returns:
            bool: True if the upload was successful, False otherwise.
        """
        self._logger.debug("Uploading files to S3")

        all_done = True

        # upload files to S3
        for file in os.listdir(self._download_folder_path):
            if not os.path.isfile(os.path.join(self._download_folder_path, file)):
                continue

            if not file.endswith(self.file_extension):
                continue

            with open(os.path.join(self._download_folder_path, file), "rb") as f:
                result = self._s3_client.upload_content(self.bucket_key, file, f.read())
                if not result:
                    all_done = False

            # Sleep after each successful download to avoid overwhelming the server
            time.sleep(random.uniform(2, 5))

        # remove the entire download folder
        shutil.rmtree(self._download_folder_path)

        return all_done
