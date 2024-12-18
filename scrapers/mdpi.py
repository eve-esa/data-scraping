import time
from typing import Dict, List, Type

from scrapers.base import BaseScraper, BaseConfigScraper
from storage import PDFName


class MDPIJournal(BaseConfigScraper):
    url: str
    name: str
    start_volume: int | None = 1
    end_volume: int | None = 16
    start_issue: int | None = 1
    end_issue: int | None = 30


class MDPIConfig(BaseConfigScraper):
    journals: List[MDPIJournal]


class MDPIScraper(BaseScraper):
    @property
    def model_class(self) -> Type[BaseConfigScraper]:
        """
        Return the configuration model class.

        Returns:
            Type[BaseConfigScraper]: The configuration model class.
        """
        return MDPIConfig

    @property
    def cookie_selector(self) -> str:
        return ""

    def scrape(self, model: MDPIConfig) -> Dict[str, Dict[int, Dict[int, List[str]]]]:
        """
        Scrape the MDPI journals for PDF links.

        Args:
            model (MDPIConfig): The configuration model.

        Returns:
            Dict[str, Dict[int, Dict[int, List[str]]]]: A dictionary containing the PDF links.
        """
        links = {}

        for journal in model.journals:
            links[journal.name] = self.__scrape_journal(journal)

        return links

    def post_process(self, links: Dict[str, Dict[int, Dict[int, List[str]]]]) -> List[str]:
        """
        Extract the PDF links from the dictionary.

        Args:
            links: A dictionary containing the PDF links.

        Returns:
            List[str]: A list of strings containing the PDF links
        """
        return [link for journal in links.values() for volume in journal.values() for issue in volume.values() for link in issue]

    def upload_to_s3(self, links: Dict[str, Dict[int, Dict[int, List[str]]]]):
        """
        Upload the PDF files to S3.

        Args:
            links (Dict[str, Dict[int, Dict[int, List[str]]]): A dictionary containing the PDF links.
        """
        self._logger.info("Uploading files to S3")

        for journal, volumes in links.items():
            for volume_num, issues in volumes.items():
                for issue_num, issue_links in issues.items():
                    for link in issue_links:
                        result = self._s3_client.upload(
                            "mdpi", link, PDFName(journal=journal, volume=str(volume_num), issue=str(issue_num))
                        )

                        if not result:
                            self._done = False

                        # Sleep after each successful download to avoid overwhelming the server
                        time.sleep(5)

    def __scrape_journal(self, journal: MDPIJournal) -> Dict[int, Dict[int, List[str]]]:
        """
        Scrape all volumes of a journal.

        Args:
            journal (MDPIJournal): The journal to scrape.

        Returns:
            Dict[int, Dict[int, List[str]]]: A dictionary containing the PDF links.
        """
        self._logger.info(f"Processing Journal {journal.name}")

        start_volume = journal.start_volume
        end_volume = journal.end_volume

        start_issue = journal.start_issue
        end_issue = journal.end_issue

        journal_url = journal.url

        return {
            volume_num: self.__scrape_volume(journal_url, start_issue, end_issue, volume_num)
            for volume_num in range(start_volume, end_volume + 1)
        }

    def __scrape_volume(
        self,
        journal_url: str,
        start_issue: int,
        end_issue: int,
        volume_num: int
    ) -> Dict[int, List]:
        """
        Scrape all issues of a volume.

        Args:
            journal_url (str): The URL of the journal.
            start_issue (int): The starting issue number.
            end_issue (int): The ending issue number.
            volume_num (int): The volume number.

        Returns:
            Dict[int, List]: A dictionary containing the PDF links.
        """
        self._logger.info(f"Processing Volume {volume_num}")
        return {
            issue_num: sir
            for issue_num in range(start_issue, end_issue + 1)
            if (sir := self.__scrape_issue(journal_url, volume_num, issue_num))
        }

    def __scrape_issue(
        self,
        journal_url: str,
        volume_num: int,
        issue_num: int
    ) -> List | None:
        """
        Scrape the issue URL for PDF links.

        Args:
            journal_url (str): The URL of the journal.
            volume_num (int): The volume number.
            issue_num (int): The issue number.

        Returns:
            List: A list of PDF links found in the issue.
        """
        issue_url = f"{journal_url}/{volume_num}/{issue_num}"
        self._logger.info(f"Processing Issue URL: {issue_url}")

        scraper = self._setup_scraper(issue_url)
        try:
            # Get all PDF links using Selenium to scroll and handle cookie popup once
            # Now find all PDF links using the class_="UD_Listings_ArticlePDF"
            pdf_links = scraper.find_all("a", class_="UD_Listings_ArticlePDF")
            pdf_links = [tag.get("href") for tag in pdf_links if tag.get("href")]
            base_url = "https://www.mdpi.com"
            pdf_links = [
                base_url + href if href.startswith("/") else href for href in pdf_links
            ]

            self._logger.info(f"PDF links found: {len(pdf_links)}")

            # If no PDF links are found, skip to the next volume
            if not pdf_links:
                self._logger.info(
                    f"No PDF links found for Issue {issue_num} in Volume {volume_num}. Skipping to the next volume."
                )
                return None

            return pdf_links
        except Exception as e:
            self._logger.error(
                f"Failed to process Issue {issue_num} in Volume {volume_num}. Error: {e}"
            )
            self._done = False
            return None
