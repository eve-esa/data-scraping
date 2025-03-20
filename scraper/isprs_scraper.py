from typing import Type, List

from helper.utils import get_scraped_url_by_bs_tag
from model.isprs_models import ISPRSConfig
from model.sql_models import ScraperFailure
from scraper.base_scraper import BaseScraper


class ISPRSScraper(BaseScraper):
    @property
    def config_model_type(self) -> Type[ISPRSConfig]:
        return ISPRSConfig

    def scrape(self) -> List[str] | None:
        pdf_tags = []
        for source in self._config_model.sources:
            self._logger.info(f"Scraping URL: {source.url}")
            try:
                scraper = self._scrape_url(source.url)

                archive_links = [tag.get("href") for tag in scraper.find_all(
                    "a", href=lambda href: href and "isprs-archives" in href and "search" not in href
                )]
                pdf_tags.extend(self.__scrape_archives(archive_links))

                proceedings_links = [
                    get_scraped_url_by_bs_tag(tag, self._config_model.base_url)
                    for tag in scraper.find_all(
                        "a", href=lambda href: href and "www.isprs.org" in href and "proceedings" in href
                    )
                ]
                if not (tags := self.__scrape_proceedings(proceedings_links)):
                    self._save_failure(source.url)
                pdf_tags.extend(tags)
            except Exception as e:
                self._log_and_save_failure(source.url, f"An error occurred while scraping the URL: {source.url}. Error: {e}")

        return pdf_tags if pdf_tags else None

    def scrape_failure(self, failure: ScraperFailure) -> List[str]:
        link = failure.source
        self._logger.info(f"Scraping URL: {link}")

        message = failure.message.lower()
        if "archive" in message:
            return self.__scrape_archives([link])

        if "proceedings" in message:
            return self.__scrape_proceedings([link])

        result = self.__scrape_archive_article(link)
        return [result] if result else []

    def __scrape_archives(self, archive_links: List[str]) -> List[str]:
        """
        Scrape the archives for PDF links. The archives contain links to articles, which in turn contain the PDF links.

        Args:
            archive_links (List[str]): A list of archive links.

        Returns:
            List[str]: A list of PDF links found in the archives.
        """
        result = []

        for link in archive_links:
            self._logger.info(f"Scraping archive: {link}")

            archive_result = []
            try:
                scraper = self._scrape_url(link)

                article_tags = scraper.find_all("a", href=True, class_="article-title")
                for article_tag in article_tags:
                    article_link = article_tag.get("href")
                    self._logger.info(f"Scraping archive's article: {article_link}")

                    if not (pdf_link := self.__scrape_archive_article(article_link)):
                        continue

                    archive_result.append(pdf_link)
            except Exception as e:
                self._log_and_save_failure(link, f"An error occurred while scraping the archive {link}: {e}")

            self._logger.info(f"Scraped {len(archive_result)} articles from {link}")
            result.extend(archive_result)

        self._logger.info(f"Scraped {len(result)} articles from {len(archive_links)} archives")
        return result

    def __scrape_archive_article(self, article_link: str) -> str | None:
        """
        Scrape a single article from the archives. The article contains the PDF link. If the article does not contain a
        PDF link, it will be saved as a failure.

        Args:
            article_link (str): The article link to scrape.

        Returns:
            str | None: The PDF link found in the article.
        """
        try:
            scraper = self._scrape_url(article_link)

            if (pdf_tag := scraper.find(
                "a",
                href=lambda href: href and ".pdf" in href,
                class_=lambda class_: class_ and "pdf-icon" in class_
            )):
                return pdf_tag.get("href")

            self._save_failure(article_link)
            return None
        except Exception as e:
            self._log_and_save_failure(article_link, f"An error occurred while scraping the article {article_link}: {e}")
            return None

    def __scrape_proceedings(self, proceedings_urls: List[str]) -> List[str]:
        """
        Scrape the proceedings for PDF links. The proceedings contain links to articles, which in turn contain the PDF
        links.

        Args:
            proceedings_urls (List[str]): A list of proceedings links.

        Returns:
            List[str]: A list of PDF links found in the proceedings
        """
        result = []

        for url in proceedings_urls:
            self._logger.info(f"Scraping proceedings: {url}")
            url_last_part = url.split("/")[-1]
            base_url = url.replace(url_last_part, "") if "." in url_last_part else url

            try:
                scraper = self._scrape_url(url)

                result.extend([
                    get_scraped_url_by_bs_tag(tag, base_url)
                    for tag in scraper.find_all("a", href=lambda href: href and ".pdf" in href)
                ])
            except Exception as e:
                self._log_and_save_failure(url, f"An error occurred while scraping the proceedings {url}: {e}")

        self._logger.info(f"Scraped {len(result)} articles from {len(proceedings_urls)} proceedings")
        return result

    def post_process(self, scrape_output: List[str]) -> List[str]:
        return scrape_output
