from typing import List
from bs4 import ResultSet

from scrapers.base_publisher_scraper import BasePublisherSource, BasePublisherScraper, SourceType


class SpringerScraper(BasePublisherScraper):
    @property
    def cookie_selector(self) -> str:
        return "button.cc-banner__button-accept"

    def _scrape_journal(self, source: BasePublisherSource) -> List[ResultSet]:
        """
        Scrape all articles of a journal. This method is called when the journal_url is provided in the config.

        Args:
            source (SpringerSource): The journal to scrape.

        Returns:
            List[ResultSet]: A list of PDF links found in the journal.
        """
        self._logger.info(f"Processing Journal {source.url}")

        next_page = True
        pdf_links = []

        try:
            counter = 1
            article_links = []
            while next_page:
                scraper = self._setup_scraper(f"{source.url}?filterOpenAccess=false&page={counter}")

                # Find all article links using appropriate class or tag
                article_links.extend(scraper.find_all("a", href=lambda href: href and "/article/" in href))

                next_page = len(article_links) > 0
                counter += 1

            pdf_links = [self._scrape_article(
                BasePublisherSource(url=link.get("href"), type=str(SourceType.ARTICLE))
            ) for link in article_links]
            pdf_links = [link for link in pdf_links if link]

            self._logger.info(f"PDF links found: {pdf_links}")
        except Exception as e:
            self._logger.error(f"Failed to process Journal {source.url}. Error: {e}")
            self._done = False

        return pdf_links

    def _scrape_issue(self, source: BasePublisherSource) -> List[ResultSet]:
        """
        Scrape a single issue of a journal. This method is called when the issue_url is provided in the config.

        Args:
            source (SpringerSource): The issue to scrape.

        Returns:
            List[ResultSet]: A list of PDF links found in the issue.
        """
        self._logger.info(f"Processing Issue {source.url}")

        scraper = self._setup_scraper(source.url)
        pdf_links = []
        try:
            # Find all PDF links using appropriate class or tag
            pdf_links = scraper.find_all("a", href=lambda href: href and "/pdf/" in href)
            self._logger.info(f"PDF links found: {len(pdf_links)}")
        except Exception as e:
            self._logger.error(f"Failed to process Issue {source.url}. Error: {e}")
            self._done = False

        return pdf_links

    def _scrape_article(self, source: BasePublisherSource) -> ResultSet | None:
        """
        Scrape a single article.

        Args:
            source (SpringerSource): The article to scrape.

        Returns:
            ResultSet: The PDF link found in the article, or None if no link is found.
        """
        self._logger.info(f"Processing Article {source.url}")

        scraper = self._setup_scraper(source.url)
        pdf_link = None
        try:
            # Find the PDF link using appropriate class or tag
            pdf_links = scraper.find_all("a", href=lambda href: href and "/pdf/" in href)
            self._logger.info(f"PDF links found: {pdf_links}")

            pdf_link = pdf_links[0] if pdf_links else None
        except Exception as e:
            self._logger.error(f"Failed to process Article {source.url}. Error: {e}")
            self._done = False

        return pdf_link
