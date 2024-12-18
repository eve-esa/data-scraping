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
        return SpringerConfig

    def scrape(self, model: SpringerConfig) -> List[ResultSet]:
        pdf_links = []
        for journal in model.elements:
            if journal.issue_url:
                pdf_links.extend(self.__scrape_issue(journal))
            elif journal.journal_url:
                pdf_links.extend(self.__scrape_journal(journal))
            else:
                pdf_links.append(self.__scrape_article(journal))

        return pdf_links

    def post_process(self, links: ResultSet) -> List[str]:
        return [link.get("href") for link in links]

    def upload_to_s3(self, links: ResultSet):
        for link in links:
            self._s3_client.upload("iop", link.get("href"))
            # Sleep after each successful download to avoid overwhelming the server
            time.sleep(5)

    def __scrape_issue(self, journal: SpringerElement) -> List[ResultSet]:
        """
        Scrape a single issue of a journal. This method is called when the issue_url is provided in the config.

        Args:
            journal (SpringerElement): The journal to scrape.

        Returns:
            List[ResultSet]: A list of PDF links found in the issue.
        """
        scraper = self._setup_scraper(journal.issue_url)

        # Find all PDF links using appropriate class or tag
        pdf_links = scraper.find_all("a", href=lambda href: href and "/article/" in href)
        self._logger.info(f"PDF links found: {len(pdf_links)}")

        self._driver.quit()

        return pdf_links

    def __scrape_journal(self, journal: SpringerElement) -> List[ResultSet]:
        """
        Scrape all articles of a journal. This method is called when the journal_url is provided in the config.

        Args:
            journal (SpringerElement): The journal to scrape.

        Returns:
            List[ResultSet]: A list of PDF links found in the journal.
        """
        next_page = True

        counter = 1
        article_links = []
        while next_page:
            scraper = self._setup_scraper(f"{journal.journal}?filterOpenAccess=false&page={counter}")

            # Find all article links using appropriate class or tag
            article_links.extend(scraper.find_all("a", href=lambda href: href and "/article/" in href))

            next_page = len(article_links) > 0

        pdf_links = [self.__scrape_article(SpringerElement(article_url=link.get("href")), True) for link in article_links]
        pdf_links = [link for link in pdf_links if link]

        self._logger.info(f"PDF links found: {pdf_links}")

        self._driver.quit()

        return pdf_links

    def __scrape_article(self, article: SpringerElement, from_journal: bool = False) -> ResultSet | None:
        """
        Scrape a single article.

        Args:
            article (SpringerElement): The article to scrape.
            from_journal (bool): Whether the article is being scraped from a journal page.

        Returns:
            ResultSet: The PDF link found in the article, or None if no link is found.
        """
        scraper = self._setup_scraper(article.issue_url)

        # Find the PDF link using appropriate class or tag
        pdf_links = scraper.find_all("a", href=lambda href: href and "/pdf/" in href)
        self._logger.info(f"PDF links found: {pdf_links}")

        if not from_journal:
            self._driver.quit()

        return pdf_links[0] if pdf_links else None
