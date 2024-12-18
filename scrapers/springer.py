import time
from typing import Type, List
from bs4 import ResultSet
from pydantic import model_validator

from scrapers.base import BaseConfigScraper, BaseScraper


class SpringerElement(BaseConfigScraper):
    issue_url: str | None = None  # url contains volume and issue number. Eg. https://link.springer.com/journal/12525/1/1
    journal_url: str | None = None  # url contains only journal name. Eg. https://link.springer.com/journal/12525
    article_url: str | None = None  # url contains only article name. Eg. https://link.springer.com/article/10.1007/s10878-021-00700-0

    @model_validator(mode="after")
    def validate_urls(self):
        if not self.issue_url and not self.journal_url and not self.article_url:
            raise ValueError("At least one of the following fields must be provided: issue_url, journal_url, article_url")

        # check that only one of the fields is provided
        if sum([bool(self.issue_url), bool(self.journal_url), bool(self.article_url)]) != 1:
            raise ValueError("Only one of the following fields must be provided: issue_url, journal_url, article_url")

        return self


class SpringerConfig(BaseConfigScraper):
    elements: List[SpringerElement]


class SpringerScraper(BaseScraper):
    @property
    def model_class(self) -> Type[BaseConfigScraper]:
        """
        Return the configuration model class.

        Returns:
            Type[BaseConfigScraper]: The configuration model class.
        """
        return SpringerConfig

    @property
    def cookie_selector(self) -> str:
        return "button.cc-banner__button-accept"

    def scrape(self, model: SpringerConfig) -> List[ResultSet]:
        """
        Scrape the Springer issue / journal / article URLs of for PDF links.

        Args:
            model (SpringerConfig): The configuration model.

        Returns:
            List[ResultSet]: A list of ResultSet objects containing the PDF links
        """
        pdf_links = []
        for element in model.elements:
            if element.issue_url:
                pdf_links.extend(self.__scrape_issue(element))
            elif element.journal_url:
                pdf_links.extend(self.__scrape_journal(element))
            else:
                pdf_links.append(self.__scrape_article(element))

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

    def upload_to_s3(self, links: ResultSet):
        """
        Upload the PDF files to S3.

        Args:
            links (ResultSet): A ResultSet object containing the PDF links.
        """
        self._logger.info("Uploading files to S3")

        for link in links:
            result = self._s3_client.upload("iop", link.get("href"))
            if not result:
                self._done = False

            # Sleep after each successful download to avoid overwhelming the server
            time.sleep(5)

    def __scrape_issue(self, element: SpringerElement) -> List[ResultSet]:
        """
        Scrape a single issue of a journal. This method is called when the issue_url is provided in the config.

        Args:
            element (SpringerElement): The journal to scrape.

        Returns:
            List[ResultSet]: A list of PDF links found in the issue.
        """
        self._logger.info(f"Processing Issue {element.issue_url}")

        scraper = self._setup_scraper(element.issue_url)
        pdf_links = []
        try:
            # Find all PDF links using appropriate class or tag
            pdf_links = scraper.find_all("a", href=lambda href: href and "/article/" in href)
            self._logger.info(f"PDF links found: {len(pdf_links)}")
        except Exception as e:
            self._logger.error(f"Failed to process Issue {element.issue_url}. Error: {e}")
            self._done = False

        return pdf_links

    def __scrape_journal(self, element: SpringerElement) -> List[ResultSet]:
        """
        Scrape all articles of a journal. This method is called when the journal_url is provided in the config.

        Args:
            element (SpringerElement): The journal to scrape.

        Returns:
            List[ResultSet]: A list of PDF links found in the journal.
        """
        self._logger.info(f"Processing Journal {element.journal_url}")

        next_page = True
        pdf_links = []

        try:
            counter = 1
            article_links = []
            while next_page:
                scraper = self._setup_scraper(f"{element.journal_url}?filterOpenAccess=false&page={counter}")

                # Find all article links using appropriate class or tag
                article_links.extend(scraper.find_all("a", href=lambda href: href and "/article/" in href))

                next_page = len(article_links) > 0
                counter += 1

            pdf_links = [self.__scrape_article(SpringerElement(article_url=link.get("href"))) for link in article_links]
            pdf_links = [link for link in pdf_links if link]

            self._logger.info(f"PDF links found: {pdf_links}")
        except Exception as e:
            self._logger.error(f"Failed to process Journal {element.journal_url}. Error: {e}")
            self._done = False

        return pdf_links

    def __scrape_article(self, element: SpringerElement) -> ResultSet | None:
        """
        Scrape a single article.

        Args:
            element (SpringerElement): The article to scrape.

        Returns:
            ResultSet: The PDF link found in the article, or None if no link is found.
        """
        self._logger.info(f"Processing Article {element.article_url}")

        scraper = self._setup_scraper(element.article_url)
        pdf_link = None
        try:
            # Find the PDF link using appropriate class or tag
            pdf_links = scraper.find_all("a", href=lambda href: href and "/pdf/" in href)
            self._logger.info(f"PDF links found: {pdf_links}")

            pdf_link = pdf_links[0] if pdf_links else None
        except Exception as e:
            self._logger.error(f"Failed to process Article {element.article_url}. Error: {e}")
            self._done = False

        return pdf_link
