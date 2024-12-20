import time
from abc import abstractmethod
from typing import List, Type, Dict
from bs4 import ResultSet, Tag
from pydantic import Field, BaseModel, field_validator

from scrapers.base_scraper import BaseScraper, BaseConfigScraper


class BasePaginationPublisherQuery(BaseModel):
    """
    Configuration model for a query to apply to a URL. The query is applied to the URL, and it can contain parameters.
    Each parameter must be enclosed in curly braces. For example, if the query is "page/{page}", the parameter "page"
    must be specified in the `params` dictionary.

    Variables:
        query (str): The query to apply to the URL.
        params (Dict[str, str] | None): The parameters to apply to the query. Default is None.
    """
    query: str
    params: Dict[str, str] | None = Field(default=None)


class BasePaginationPublisherConfig(BaseConfigScraper):
    """
    Configuration model for a pagination publisher scraper. It is possible to specify up to two queries, one for the
    first page and one for the rest. The queries are applied to the URL. The URL is the URL of the main page of the
    pagination.

    Variables:
        url (str): The URL of the publisher.
        queries (List[BasePaginationPublisherQuery] | None): The queries to apply to the URL. Default is None.
    """
    url: str
    queries: List[BasePaginationPublisherQuery] | None = Field(default=None)

    @field_validator("queries")
    def validate_type(cls, v):
        if len(v) > 2:
            raise ValueError(f"You can specify at most two queries, one for the first page and one for the rest. "
                             f"Received {len(v)} queries.")
        return v


class BaseUrlPublisherScraper(BaseScraper):
    @property
    def model_class(self) -> Type[BasePaginationPublisherConfig]:
        """
        Return the configuration model class.

        Returns:
            Type[BasePaginationPublisherConfig]: The configuration model class.
        """
        return BasePaginationPublisherConfig

    def scrape(self, model: BasePaginationPublisherConfig) -> ResultSet | List[Tag]:
        """
        Scrape the source URLs of for PDF links.

        Args:
            model (BaseUrlPublisherConfig): The configuration model.

        Returns:
            ResultSet | List[Tag]: A ResultSet (i.e., a list) or a list of Tag objects containing the tags to the PDF
                links.
        """
        pass

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

    def upload_to_s3(self, pdf_tag_list: ResultSet | List[Tag], model: BasePaginationPublisherConfig):
        """
        Upload the PDF files to S3.

        Args:
            pdf_tag_list (ResultSet | List[Tag]): A ResultSet (i.e., a list) or a list of Tag objects containing the
            model (BaseUrlPublisherConfig): The configuration model.
        """
        self._logger.info("Uploading files to S3")

        for tag in pdf_tag_list:
            result = self._s3_client.upload(model.bucket_key, tag.get("href"))
            if not result:
                self._done = False

            # Sleep after each successful download to avoid overwhelming the server
            time.sleep(5)

    def _parse_query_with_params(self, query_model: BasePaginationPublisherQuery) -> str:
        """
        Parse the query with the parameters. The parameters must be enclosed in curly braces.

        Args:
            query_model (BasePaginationPublisherQuery): The query model.

        Returns:
            str: The parsed query.
        """
        if not query_model.params:
            return query_model.query

        return query_model.query.format(**query_model.params)

    @abstractmethod
    def _scrape_pagination(self, source: BasePaginationPublisherConfig) -> ResultSet:
        """
        Scrape all the pages of the paginated URLs identified by the `source.url` plus the queries.

        Args:
            source (BasePaginationPublisherConfig): The source to scrape.

        Returns:
            ResultSet: A ResultSet (i.e., a list) of objects containing the PDF links.
        """
        pass

    @abstractmethod
    def _scrape_page(self, source: BasePaginationPublisherConfig) -> ResultSet:
        """
        Scrape the single page of the paginated URLs identified by the `source.url` plus the queries.

        Args:
            source (BasePaginationPublisherConfig): The issue to scrape.

        Returns:
            ResultSet: A ResultSet (i.e., list) object containing the tags to the PDF links.
        """
        pass
