from typing import Type, List

from helper.utils import get_scraped_url_by_bs_tag
from model.elsevier_models import (
    SourceType,
    ElsevierConfig,
    ElsevierScraperOutput,
    ElsevierSource,
    ElsevierScrapeIssueOutput,
)
from model.sql_models import ScraperFailure
from scraper.base_source_download_scraper import BaseSourceDownloadScraper


class ElsevierScraper(BaseSourceDownloadScraper):
    def __init__(self):
        super().__init__()
        self.__error_on_no_first_issue_tag = "No issue found"

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

    def scrape_link(self, failure: ScraperFailure) -> List[str]:
        link = failure.source
        self._logger.info(f"Scraping URL: {link}")

        error = failure.message.lower()

        if "journal" in error or self.__error_on_no_first_issue_tag in error:
            source = ElsevierSource(url=link, name="Elsevier", type=str(SourceType.JOURNAL))
            result = self.__scrape_journal(source)
            return result if result is not None else []

        source = ElsevierSource(url=link, name="Elsevier", type=str(SourceType.ISSUE))
        result = self.__scrape_issue(source)
        return result.pdf_links if result.pdf_links else []

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

    def _get_file_path_from_link(self, link: str) -> str | None:
        try:
            pid = link.split("pid=")[1].split("&")[0]
        except:
            return None

        file_path = None
        try:
            # visit the PDF link
            self._driver.cdp.open(link)
            file_path = self._wait_end_download(pid)
        except Exception as e:
            self._logger.error(f"Error uploading to S3: {e}")
        finally:
            return file_path
