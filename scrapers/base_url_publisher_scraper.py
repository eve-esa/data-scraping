from abc import abstractmethod
from typing import List, Type
from bs4 import ResultSet, Tag
from pydantic import BaseModel, field_validator

from base_enum import Enum
from scrapers.base_scraper import BaseScraper, BaseConfigScraper
from utils import get_scraped_url


class SourceType(Enum):
    ISSUE = "issue"
    JOURNAL = "journal"
    ARTICLE = "article"


class BaseUrlPublisherSource(BaseModel):
    url: str
    type: str

    @field_validator("type")
    def validate_type(cls, v):
        if not v:
            raise ValueError("Type cannot be empty")
        if v not in SourceType:
            raise ValueError(f"Invalid type: {v}")
        return v


class BaseUrlPublisherConfig(BaseConfigScraper):
    sources: List[BaseUrlPublisherSource]


class BaseUrlPublisherScraper(BaseScraper):
    @property
    def config_model_type(self) -> Type[BaseUrlPublisherConfig]:
        """
        Return the configuration model type. This method must be implemented in the derived class.

        Returns:
            Type[BaseUrlPublisherConfig]: The configuration model type
        """
        return BaseUrlPublisherConfig

    def scrape(self, model: BaseUrlPublisherConfig) -> ResultSet | List[Tag] | None:
        """
        Scrape the source URLs of for PDF links.

        Args:
            model (BaseUrlPublisherConfig): The configuration model.

        Returns:
            ResultSet | List[Tag]: A ResultSet (i.e., a list) or a list of Tag objects containing the tags to the PDF links. If no tag was found, return None.
        """
        pdf_tags = []
        for source in model.sources:
            if source.type == SourceType.ISSUE:
                scraped_tags = self._scrape_issue(source)
            elif source.type == SourceType.JOURNAL:
                scraped_tags = self._scrape_journal(source)
            else:
                scraped_tag = self._scrape_article(source)
                scraped_tags = [scraped_tag] if scraped_tag is not None else None

            if scraped_tags is not None:
                pdf_tags.extend(scraped_tags)

        return pdf_tags if pdf_tags else None

    def post_process(self, scrape_output: ResultSet | List[Tag]) -> List[str]:
        """
        Extract the href attribute from the links.

        Args:
            scrape_output (ResultSet | List[Tag]): A ResultSet (i.e., a list) or a list of Tag objects containing the tags to the PDF links.

        Returns:
            List[str]: A list of strings containing the PDF links
        """
        return [get_scraped_url(tag, self.base_url) for tag in scrape_output]

    @abstractmethod
    def _scrape_journal(self, source: BaseUrlPublisherSource) -> ResultSet | List[Tag] | None:
        """
        Scrape all articles of a journal. This method is called when the journal_url is provided in the config.

        Args:
            source (BaseUrlPublisherSource): The journal to scrape.

        Returns:
            ResultSet | List[Tag]: A ResultSet (i.e., a list) or a list of Tag objects containing the PDF links. If no tag was found, return None.
        """
        pass

    @abstractmethod
    def _scrape_issue(self, source: BaseUrlPublisherSource) -> ResultSet | None:
        """
        Scrape the issue URL for PDF links.

        Args:
            source (BaseUrlPublisherSource): The issue to scrape.

        Returns:
            ResultSet: A ResultSet (i.e., list) object containing the tags to the PDF links, or None if no tag was found.
        """
        pass

    @abstractmethod
    def _scrape_article(self, element: BaseUrlPublisherSource) -> Tag | None:
        """
        Scrape a single article.

        Args:
            element (BaseUrlPublisherSource): The article to scrape.

        Returns:
            Tag | None: The tag containing the PDF link found in the article, or None if no tag was found.
        """
        pass
