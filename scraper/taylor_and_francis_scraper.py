from typing import List, Type
from bs4 import Tag

from helper.utils import get_scraped_url
from model.base_url_publisher_models import BaseUrlPublisherConfig
from scraper.base_url_publisher_scraper import BaseUrlPublisherScraper, BaseUrlPublisherSource, SourceType


class TaylorAndFrancisScraper(BaseUrlPublisherScraper):
    @property
    def config_model_type(self) -> Type[BaseUrlPublisherConfig]:
        """
        Return the configuration model type.

        Returns:
            Type[BaseUrlPublisherConfig]: The configuration model type
        """
        return BaseUrlPublisherConfig

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
            self._scrape_url(source.url)

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

            # Find all PDF links using appropriate class or tag (if lambda returns True, it will be included in the list)
            issues_tag_list = self._get_parsed_page_source().find_all("a", href=True, class_="issue-link")

            # For each tag of issues previously collected, scrape the issue as a collection of articles
            pdf_tag_list = [
                tag
                for x in issues_tag_list
                if (
                    tags := self._scrape_issue_or_collection(BaseUrlPublisherSource(
                        url=get_scraped_url(x, self._config_model.base_url), type=str(SourceType.ISSUE_OR_COLLECTION)
                    ))
                )
                for tag in tags
            ]
            self._logger.debug(f"PDF links found: {len(pdf_tag_list)}")

            return pdf_tag_list
        except Exception as e:
            self._logger.error(f"Failed to process Journal {source.url}. Error: {e}")
            return None

    def _scrape_issue_or_collection(self, source: BaseUrlPublisherSource) -> List[Tag] | None:
        """
        Scrape the issue (or collection) URL for PDF links.

        Args:
            source (BaseUrlPublisherSource): The issue / collection to scrape.

        Returns:
            List[Tag] | None: A list of Tag objects containing the tags to the PDF links, or None if no tag was found.
        """
        self._logger.info(f"Processing Issue / Collection {source.url}")

        try:
            scraper = self._scrape_url(source.url)

            # Find all PDF links using appropriate class or tag (if lambda returns True, it will be included in the list)
            article_tag_list = scraper.find_all(
                "a",
                href=lambda href: href and "/doi/full/" in href,
                class_=lambda class_: class_ and "ref nowrap" in class_,
            )

            # For each tag of articles previously collected, scrape the article
            pdf_tag_list = [
                tag
                for x in article_tag_list
                if (
                    tag := self._scrape_article(BaseUrlPublisherSource(
                        url=get_scraped_url(x, self._config_model.base_url), type=str(SourceType.ARTICLE)
                    ))
                )
            ]
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
        self._logger.info(f"Processing Article {source.url}")

        try:
            scraper = self._scrape_url(source.url)

            # Find the PDF link using appropriate class or tag (if lambda returns True, it will be included in the list)
            return scraper.find("a", href=lambda href: href and "/doi/" in href and "/pdf/" in href, class_="show-pdf")
        except Exception as e:
            self._logger.error(f"Failed to process Article {source.url}. Error: {e}")
            return None
