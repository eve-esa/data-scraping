from typing import Type, List

from helper.utils import get_scraped_url
from model.isprs_models import ISPRSConfig
from scraper.base_scraper import BaseScraper


class ISPRSScraper(BaseScraper):
    @property
    def config_model_type(self) -> Type[ISPRSConfig]:
        return ISPRSConfig

    def scrape(self, model: ISPRSConfig) -> List[str] | None:
        pdf_tags = []
        for source in model.sources:
            try:
                self._logger.info(f"Scraping URL: {source.url}")

                scraper, driver = self._scrape_url(source.url)
                driver.quit()

                archive_links = [tag.get("href") for tag in scraper.find_all(
                    "a", href=lambda href: href and "isprs-archives" in href and "search" not in href
                )]
                pdf_tags.extend(self.__scrape_archives(archive_links))

                proceedings_links = [get_scraped_url(tag, self.base_url) for tag in scraper.find_all(
                    "a", href=lambda href: href and "www.isprs.org" in href and "proceedings" in href
                )]
                pdf_tags.extend(self.__scrape_proceedings(proceedings_links))
            except Exception as e:
                self._logger(f"An error occurred while scraping the URL: {source.url}. Error: {e}")

        return pdf_tags if pdf_tags else None

    def __scrape_archives(self, archive_links: List[str]) -> List[str]:
        result = []

        for link in archive_links:
            self._logger.info(f"Scraping archive: {link}")

            archive_result = []
            try:
                scraper, driver = self._scrape_url(link)
                driver.quit()

                article_tags = scraper.find_all("a", href=True, class_="article-title")
                for article_tag in article_tags:
                    article_link = article_tag.get("href")
                    self._logger.info(f"Scraping archive's article: {article_link}")

                    if pdf_link := self.__scrape_archive_article(article_link):
                        archive_result.append(pdf_link)
            except Exception as e:
                self._logger.error(f"An error occurred while scraping the archive {link}: {e}")

            self._logger.info(f"Scraped {len(archive_result)} articles from {link}")
            result.extend(archive_result)

        self._logger.info(f"Scraped {len(result)} articles from {len(archive_links)} archives")
        return result

    def __scrape_archive_article(self, article_link: str) -> str | None:
        try:
            scraper, driver = self._scrape_url(article_link)
            driver.quit()

            if (pdf_tag := scraper.find(
                "a",
                href=lambda href: href and ".pdf" in href,
                class_=lambda class_: class_ and "pdf-icon" in class_
            )):
                return pdf_tag.get("href")
            return None
        except Exception as e:
            self._logger.error(f"An error occurred while scraping the article {article_link}: {e}")
            return None

    def __scrape_proceedings(self, proceedings_links: List[str]) -> List[str]:
        result = []

        for link in proceedings_links:
            self._logger.info(f"Scraping proceedings: {link}")

            try:
                scraper, driver = self._scrape_url(link)
                driver.quit()

                result.extend([
                    get_scraped_url(tag, link if link.endswith("/") else link[:link.rfind('/')])
                    for tag in scraper.find_all("a", href=lambda href: href and ".pdf" in href)
                ])
            except Exception as e:
                self._logger.error(f"An error occurred while scraping the proceedings {link}: {e}")

        self._logger.info(f"Scraped {len(result)} articles from {len(proceedings_links)} proceedings")
        return result

    def post_process(self, scrape_output: List[str]) -> List[str]:
        return scrape_output
