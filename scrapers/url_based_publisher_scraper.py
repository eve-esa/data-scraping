import time
from abc import abstractmethod
from typing import List, Type
from bs4 import ResultSet, Tag
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

    def scrape(self, model: UrlBasedPublisherConfig) -> ResultSet | List[Tag]:
        """
        Scrape the source URLs of for PDF links.

        Args:
            model (UrlBasedPublisherConfig): The configuration model.

        Returns:
            ResultSet | List[Tag]: A ResultSet (i.e., a list) or a list of Tag objects containing the tags to the PDF
                links.
        """
        pdf_tags = []
        for source in model.sources:
            if source.type == SourceType.ISSUE:
                pdf_tags.extend(self._scrape_issue(source))
            elif source.type == SourceType.JOURNAL:
                pdf_tags.extend(self._scrape_journal(source))
            elif scraped_tag := self._scrape_article(source):
                pdf_tags.append(scraped_tag)

        return pdf_tags

    def post_process(self, pdf_tag_list: ResultSet | List[Tag]) -> List[str]:
        """
        Extract the href attribute from the links.

        Args:
            pdf_tag_list (ResultSet | List[Tag]): A ResultSet (i.e., a list) or a list of Tag objects containing the
            tags to the PDF links.

        Returns:
            List[str]: A list of strings containing the PDF links
        """
        return [tag.get("href") for tag in pdf_tag_list]

    def upload_to_s3(self, pdf_tag_list: ResultSet | List[Tag], model: UrlBasedPublisherConfig):
        """
        Upload the PDF files to S3.

        Args:
            pdf_tag_list (ResultSet | List[Tag]): A ResultSet (i.e., a list) or a list of Tag objects containing the
            model (UrlBasedPublisherConfig): The configuration model.
        """
        self._logger.info("Uploading files to S3")

        for tag in pdf_tag_list:
            result = self._s3_client.upload(model.bucket_key, tag.get("href"))
            if not result:
                self._done = False

            # Sleep after each successful download to avoid overwhelming the server
            time.sleep(5)

    @abstractmethod
    def _scrape_journal(self, source: UrlBasesPublisherSource) -> ResultSet | List[Tag]:
        """
        Scrape all articles of a journal. This method is called when the journal_url is provided in the config.

        Args:
            source (UrlBasesPublisherSource): The journal to scrape.

        Returns:
            ResultSet | List[Tag]: A ResultSet (i.e., a list) or a list of Tag objects containing the PDF links.
        """
        pass

    @abstractmethod
    def _scrape_issue(self, source: UrlBasesPublisherSource) -> ResultSet:
        """
        Scrape the issue URL for PDF links.

        Args:
            source (UrlBasesPublisherSource): The issue to scrape.

        Returns:
            ResultSet: A ResultSet (i.e., list) object containing the tags to the PDF links.
        """
        pass

    @abstractmethod
    def _scrape_article(self, element: UrlBasesPublisherSource) -> Tag | None:
        """
        Scrape a single article.

        Args:
            element (UrlBasesPublisherSource): The article to scrape.

        Returns:
            Tag | None: The tag containing the PDF link found in the article, or None if no tag was found.
        """
        pass
