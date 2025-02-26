from typing import List, Type
from bs4 import Tag

from helper.utils import get_scraped_url_by_bs_tag
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

            buttons = self._driver.cdp.find_elements("li.vol_li > button.volume_link")

            issues_links = []
            for button in buttons:
                button.click()
                self._driver.cdp.sleep(2)
                issues_links.extend([
                    get_scraped_url_by_bs_tag(x, self._config_model.base_url)
                    for x in self._get_parsed_page_source().find_all("a", href=True, class_="issue-link")
                ])
            issues_links = list(set(issues_links))

            # For each tag of issues previously collected, scrape the issue as a collection of articles
            if not (pdf_tag_list := [
                tag
                for link in issues_links
                if (tags := self._scrape_issue_or_collection(
                    BaseUrlPublisherSource(url=link, type=str(SourceType.ISSUE_OR_COLLECTION))
                ))
                for tag in tags
            ]):
                self._save_failure(source.url)

            self._logger.debug(f"PDF links found: {len(pdf_tag_list)}")
            return pdf_tag_list
        except Exception as e:
            self._log_and_save_failure(source.url, f"Failed to process Journal {source.url}. Error: {e}")
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
            articles_links = [
                get_scraped_url_by_bs_tag(tag, self._config_model.base_url).replace("/doi/full/", "/doi/pdf/")
                for tag in scraper.find_all(
                    "a",
                    href=lambda href: href and "/doi/full/" in href,
                    class_=lambda class_: class_ and "ref" in class_ and "nowrap" in class_,
                )
            ]
            if not articles_links:
                self._save_failure(source.url)

            pdf_tag_list = [Tag(name="a", attrs={"href": link}) for link in articles_links]

            self._logger.debug(f"PDF links found: {len(pdf_tag_list)}")
            return pdf_tag_list
        except Exception as e:
            self._log_and_save_failure(source.url, f"Failed to process Issue / Collection {source.url}. Error: {e}")
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
            if not (tag := scraper.find("a", href=lambda href: href and "/doi/" in href and "/pdf/" in href, class_="show-pdf")):
                self._save_failure(source.url)

            return tag
        except Exception as e:
            self._log_and_save_failure(source.url, f"Failed to process Article {source.url}. Error: {e}")
            return None
