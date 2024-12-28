from typing import List
from bs4 import Tag, ResultSet, BeautifulSoup

from scraper.base_url_publisher_scraper import BaseUrlPublisherScraper, BaseUrlPublisherSource, SourceType
from utils import get_scraped_url


class TaylorAndFrancisSectionScraper(BaseUrlPublisherScraper):
    @property
    def cookie_selector(self) -> str:
        return "[id='onetrust-accept-btn-handler']"

    @property
    def base_url(self) -> str:
        return "https://www.tandfonline.com"

    def _scrape_journal(self, source: BaseUrlPublisherSource) -> ResultSet | List[Tag] | None:
        """
        Scrape all articles of a journal.

        Args:
            source (BaseUrlPublisherSource): The journal to scrape.

        Returns:
            ResultSet | List[Tag] | None: A ResultSet (i.e., a list) or a list of Tag objects containing the PDF links. If no tag was found, return None.
        """
        pass

    def _scrape_issue_or_collection(self, source: BaseUrlPublisherSource) -> List[Tag] | None:
        """
        Scrape the issue (or collection) URL for PDF links.

        Args:
            source (BaseUrlPublisherSource): The issue / collection to scrape.

        Returns:
            List[Tag] | None: A list of Tag objects containing the tags to the PDF links, or None if no tag was found.
        """
        self._logger.info(f"Processing Issue {source.url}")

        try:
            scraper = self._scrape_url_by_bs4(source.url)

            # Find all PDF links using appropriate class or tag (if lambda returns True, it will be included in the list)
            article_tag_list = scraper.find_all(
                "a",
                href=lambda href: href and "/doi/full/" in href,
                class_=lambda class_: class_ and "ref nowrap" in class_,
            )

            # For each tag of articles previously collected, scrape the article
            pdf_tag_list = [
                tag for tag in (
                    self._scrape_article(
                        BaseUrlPublisherSource(url=get_scraped_url(tag, self.base_url), type=str(SourceType.ARTICLE))
                    )
                    for tag in article_tag_list
                ) if tag
            ]
            self._logger.info(f"PDF links found: {pdf_tag_list}")

            return pdf_tag_list
        except Exception as e:
            self._logger.error(f"Failed to process Issue {source.url}. Error: {e}")
            return None

    def _scrape_article(self, source: BaseUrlPublisherSource) -> Tag | None:
        """
        Scrape a single article.

        Args:
            source (BaseUrlPublisherSource): The article to scrape.

        Returns:
            Tag | None: The tag containing the PDF link found in the article, or None if no tag was found.
        """
        self._logger.info(f"Processing Article {source.url}")

        try:
            scraper = self._scrape_url_by_bs4(source.url)

            # Find the PDF link using appropriate class or tag (if lambda returns True, it will be included in the list)
            return scraper.find("a", href=lambda href: href and "/doi/" in href and "/pdf/" in href, class_="show-pdf")
        except Exception as e:
            self._logger.error(f"Failed to process Article {source.url}. Error: {e}")
            return None


class TaylorAndFrancisJournalScraper(TaylorAndFrancisSectionScraper):
    def _scrape_journal(self, source: BaseUrlPublisherSource) -> List[Tag] | None:
        """
        Scrape all articles of a journal.

        Args:
            source (BaseUrlPublisherSource): The journal to scrape.

        Returns:
            List[Tag] | None: A list of Tag objects containing the PDF links. If no tag was found, return None.
        """
        self._logger.info(f"Processing Journal {source.url}")

        try:
            self._scrape_url_by_selenium(source.url)

            # Click all the volume links to load all the issues
            self._driver.execute_script("""
                async function clickButtons() {
                    const buttons = document.querySelectorAll('button.volume_link');
                    for (const button of buttons) {
                        button.click();
                        await new Promise(resolve => setTimeout(resolve, 1000));
                    }
                }
                return clickButtons();
            """)

            # Now that all the clicks are completed, we can get the updated source
            scraper = BeautifulSoup(self._driver.page_source, "html.parser")

            # Find all PDF links using appropriate class or tag (if lambda returns True, it will be included in the list)
            issues_tag_list = scraper.find_all("a", href=True, class_="issue-link")

            # For each tag of issues previously collected, scrape the issue as a collection of articles
            pdf_tag_list = []
            for tag in issues_tag_list:
                pdf_tag_list.extend(
                    self._scrape_issue_or_collection(
                        BaseUrlPublisherSource(url=get_scraped_url(tag, self.base_url), type=str(SourceType.ISSUE_OR_COLLECTION))
                    )
                )
            self._logger.info(f"PDF links found: {pdf_tag_list}")

            return pdf_tag_list
        except Exception as e:
            self._logger.error(f"Failed to process Issue {source.url}. Error: {e}")
            return None
