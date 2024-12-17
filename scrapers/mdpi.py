from typing import Dict, List, Type
from bs4 import BeautifulSoup

from scrapers.base import BaseScraper, BaseModelScraper


class MDPIModel(BaseModelScraper):
    journal_url: str
    start_volume: int | None = 1
    end_volume: int | None = 16
    start_issue: int | None = 1
    end_issue: int | None = 30


class MDPIScraper(BaseScraper):
    def scrape(self, model: MDPIModel, scraper: BeautifulSoup) -> List:
        start_volume = model.start_volume
        end_volume = model.end_volume

        start_issue = model.start_issue
        end_issue = model.end_issue

        journal_url = model.journal_url

        # input: complete url with only journal
        # output: list complete url with journal and volume
        links = {
            volume_num: self.__scrape_volume(scraper, journal_url, start_issue, end_issue, volume_num)
            for volume_num in range(start_volume, end_volume + 1)
        }

        self.driver.quit()

        return [link for volume in links.values() for link in volume.values()]

    def __scrape_volume(
        self,
        scraper: BeautifulSoup,
        journal_url: str,
        start_issue: int,
        end_issue: int,
        volume_num: int
    ) -> Dict[int, List]:
        self.logger.info(f"Processing Volume {volume_num}...")
        return {
            issue_num: sir
            for issue_num in range(start_issue, end_issue + 1)
            if (sir := self.__scrape_issue(scraper, journal_url, volume_num, issue_num))
        }

    def __scrape_issue(
        self,
        scraper: BeautifulSoup,
        journal_url: str,
        volume_num: int,
        issue_num: int
    ) -> List | None:
        issue_url = f"{journal_url}/{volume_num}/{issue_num}"

        self.logger.info(f"Processing Issue URL: {issue_url}")
        try:
            # Get all PDF links using Selenium to scroll and handle cookie popup once
            # Now find all PDF links using the class_="UD_Listings_ArticlePDF"
            pdf_links = scraper.find_all("a", class_="UD_Listings_ArticlePDF")
            pdf_links = [tag.get("href") for tag in pdf_links if tag.get("href")]
            base_url = "https://www.mdpi.com"
            pdf_links = [
                base_url + href if href.startswith("/") else href for href in pdf_links
            ]

            self.logger.info(f"PDF links found: {len(pdf_links)}")

            # If no PDF links are found, skip to the next volume
            if not pdf_links:
                self.logger.info(
                    f"No PDF links found for Issue {issue_num} in Volume {volume_num}. Skipping to the next volume."
                )
                return None

            return pdf_links
        except Exception as e:
            self.logger.error(
                f"Failed to process Issue {issue_num} in Volume {volume_num}. Error: {e}"
            )
            return None

    @property
    def model_class(self) -> Type[BaseModelScraper]:
        return MDPIModel