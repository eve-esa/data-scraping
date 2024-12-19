import time
from abc import abstractmethod
from typing import Dict, List, TypeAlias
from bs4 import Tag

from scrapers.base_scraper import BaseScraper, BaseConfigScraper
from storage import PDFName


IterativePublisherScrapeOutput: TypeAlias = Dict[str, Dict[int, Dict[int, List[str]]]]
IterativePublisherScrapeJournalOutput: TypeAlias = Dict[int, Dict[int, List[str]]]
IterativePublisherScrapeVolumeOutput: TypeAlias = Dict[int, List[str]]
IterativePublisherScrapeIssueOutput: TypeAlias = List[str] | None


class IterativePublisherScraper(BaseScraper):
    def post_process(self, links: IterativePublisherScrapeOutput) -> List[str]:
        """
        Extract the PDF links from the dictionary.

        Args:
            links: A dictionary containing the PDF links.

        Returns:
            List[str]: A list of strings containing the PDF links
        """
        return [link for journal in links.values() for volume in journal.values() for issue in volume.values() for link in issue]

    def upload_to_s3(self, links: IterativePublisherScrapeOutput, model: BaseConfigScraper):
        """
        Upload the PDF files to S3.

        Args:
            links (IterativePublisherScrapeOutput): A dictionary containing the PDF links.
            model (BaseConfigScraper): The configuration model.
        """
        self._logger.info("Uploading files to S3")

        for journal, volumes in links.items():
            for volume_num, issues in volumes.items():
                for issue_num, issue_links in issues.items():
                    for link in issue_links:
                        result = self._s3_client.upload(
                            model.bucket_key, link, PDFName(journal=journal, volume=str(volume_num), issue=str(issue_num))
                        )

                        if not result:
                            self._done = False

                        # Sleep after each successful download to avoid overwhelming the server
                        time.sleep(5)

    @abstractmethod
    def _scrape_journal(self, journal: BaseConfigScraper) -> IterativePublisherScrapeJournalOutput:
        """
        Scrape all volumes of a journal.

        Args:
            journal (BaseConfigScraper): The journal to scrape.

        Returns:
            IterativePublisherScrapeJournalOutput: A dictionary containing the PDF links.
        """
        pass

    @abstractmethod
    def _scrape_volume(self, *args, **kwargs) -> IterativePublisherScrapeVolumeOutput:
        """
        Scrape all issues of a volume.

        Returns:
            IterativePublisherScrapeVolumeOutput: A dictionary containing the PDF links.
        """
        pass

    @abstractmethod
    def _scrape_issue(self, *args, **kwargs) -> IterativePublisherScrapeIssueOutput:
        """
        Scrape the issue URL for PDF links.

        Returns:
            List: A list of PDF links found in the issue.
        """
        pass

    @abstractmethod
    def _scrape_article(self, *args, **kwargs) -> List[Tag]:
        """
        Scrape a single article.

        Returns:
            List[Tag]: A list of Tag objects containing the PDF links.
        """
        pass