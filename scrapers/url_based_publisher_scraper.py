import time
from abc import abstractmethod
from typing import List, Type
from bs4 import ResultSet
from pydantic import BaseModel, field_validator

from base_enum import Enum
from scrapers.base_scraper import BaseScraper, BaseConfigScraper


class SourceType(Enum):
    ISSUE = "issue"
    JOURNAL = "journal"
    ARTICLE = "article"


class UrlBasesPublisherSource(BaseModel):
    url: str
    type: str

    @field_validator("type")
    def validate_type(cls, v):
        if not v:
            raise ValueError("Type cannot be empty")
        if v not in SourceType:
            raise ValueError(f"Invalid type: {v}")
        return v


class UrlBasedPublisherConfig(BaseConfigScraper):
    sources: List[UrlBasesPublisherSource]


class UrlBasedPublisherScraper(BaseScraper):
    @property
    def model_class(self) -> Type[UrlBasedPublisherConfig]:
        """
        Return the configuration model class.

        Returns:
            Type[BaseConfigScraper]: The configuration model class.
        """
        return UrlBasedPublisherConfig

    def scrape(self, model: UrlBasedPublisherConfig) -> List[ResultSet]:
        """
        Scrape the source URLs of for PDF links.

        Args:
            model (UrlBasedPublisherConfig): The configuration model.

        Returns:
            List[ResultSet]: A list of ResultSet objects containing the PDF links.
        """
        pdf_links = []
        for source in model.sources:
            if source.type == SourceType.ISSUE:
                pdf_links.extend(self._scrape_issue(source))
            elif source.type == SourceType.JOURNAL:
                pdf_links.extend(self._scrape_journal(source))
            else:
                pdf_links.append(self._scrape_article(source))

        return pdf_links

    def post_process(self, links: ResultSet) -> List[str]:
        """
        Extract the href attribute from the links.

        Args:
            links (ResultSet): A ResultSet object containing the PDF links.

        Returns:
            List[str]: A list of strings containing the PDF links
        """
        return [link.get("href") for link in links]

    def upload_to_s3(self, links: ResultSet, model: UrlBasedPublisherConfig):
        """
        Upload the PDF files to S3.

        Args:
            links (ResultSet): A ResultSet object containing the PDF links.
            model (UrlBasedPublisherConfig): The configuration model.
        """
        self._logger.info("Uploading files to S3")

        for link in links:
            result = self._s3_client.upload(model.bucket_key, link.get("href"))
            if not result:
                self._done = False

            # Sleep after each successful download to avoid overwhelming the server
            time.sleep(5)

    @abstractmethod
    def _scrape_journal(self, source: UrlBasesPublisherSource) -> List[ResultSet]:
        """
        Scrape all articles of a journal. This method is called when the journal_url is provided in the config.

        Args:
            source (SpringerSource): The journal to scrape.

        Returns:
            List[ResultSet]: A list of PDF links found in the journal.
        """
        pass

    @abstractmethod
    def _scrape_issue(self, source: UrlBasesPublisherSource) -> List[ResultSet]:
        """
        Scrape the issue URL for PDF links.

        Args:
            source (IOPSource): The issue to scrape.

        Returns:
            List[ResultSet]: A list of ResultSet objects containing the PDF links.
        """
        pass

    @abstractmethod
    def _scrape_article(self, element: UrlBasesPublisherSource) -> ResultSet | None:
        """
        Scrape a single article.

        Args:
            element (SpringerSource): The article to scrape.

        Returns:
            ResultSet: The PDF link found in the article, or None if no link is found.
        """
        pass