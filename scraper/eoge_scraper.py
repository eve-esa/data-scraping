from typing import List
from bs4 import Tag, ResultSet

from helper.utils import get_scraped_url, get_parsed_page_source
from model.base_url_publisher_models import BaseUrlPublisherSource, SourceType
from scraper.base_url_publisher_scraper import BaseUrlPublisherScraper


class EOGEScraper(BaseUrlPublisherScraper):
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
            _, driver = self._scrape_url(source.url)

            # Click all the volume links to load all the issues
            driver.execute_script("""
                async function clickButtons() {
                    const buttons = document.querySelectorAll('a[data-toggle="collapse"]');
                    for (const button of buttons) {
                        button.click();
                        await new Promise(resolve => setTimeout(resolve, 1000));
                    }
                }
                return clickButtons();
            """)

            # Find all PDF links using appropriate class or tag (if lambda returns True, it will be included in the list)
            issues_tag_list = get_parsed_page_source(driver).find_all(
                "a", href=lambda href: href and "issue_" in href and ".html" in href
            )
            driver.quit()

            # For each tag of issues previously collected, scrape the issue as a collection of articles
            pdf_tag_list = [
                tag
                for tags in (
                    self._scrape_issue_or_collection(BaseUrlPublisherSource(
                        url=get_scraped_url(tag, self.base_url), type=str(SourceType.ISSUE_OR_COLLECTION)
                    ))
                    for tag in issues_tag_list
                )
                if tags for tag in tags]
            self._logger.debug(f"PDF links found: {len(pdf_tag_list)}")

            return pdf_tag_list
        except Exception as e:
            self._logger.error(f"Failed to process Journal {source.url}. Error: {e}")
            return None

    def _scrape_issue_or_collection(self, source: BaseUrlPublisherSource) -> ResultSet | None:
        """
        Scrape the issue (or collection) URL for PDF links.

        Args:
            source (BaseUrlPublisherSource): The issue / collection to scrape.

        Returns:
            ResultSet | None: A Result (i.e., a list) of Tag objects containing the tags to the PDF links, or None if no tag was found.
        """
        self._logger.info(f"Processing Issue / Collection {source.url}")

        try:
            scraper, driver = self._scrape_url(source.url)
            driver.quit()

            # Find all PDF links using appropriate class or tag (if lambda returns True, it will be included in the list)
            pdf_tag_list = scraper.find_all(
                "a", href=lambda href: href and "/article" in href and ".pdf" in href, class_="pdf_link"
            )
            self._logger.debug(f"PDF links found: {len(pdf_tag_list)}")

            return pdf_tag_list
        except Exception as e:
            self._logger.error(f"Failed to process Issue / Collection {source.url}. Error: {e}")
            return None

    def _scrape_article(self, source: BaseUrlPublisherSource) -> Tag | None:
        """
        Scrape a single article.

        Args:
            source (BaseUrlPublisherSource): The article to scrape.

        Returns:
            Tag | None: The tag containing the PDF link found in the article, or None if no tag was found.
        """
        pass