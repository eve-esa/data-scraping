import time
from typing import Dict, List, Type
from bs4 import BeautifulSoup
from pydantic import BaseModel

from scrapers.base import BaseScraper


class MDPIModel(BaseModel):
    journal_url: str
    start_volume: int | None = 1
    end_volume: int | None = 16
    start_issue: int | None = 1
    end_issue: int | None = 30


class MDPIScraper(BaseScraper):
    # get paper url list from issue
    def scrape(self, issue_url: str) -> list:
        """return list of urls ready to download

        Args:
            issue_url (str): url contains volume and issue number. Eg:https://www.mdpi.com/2072-4292/1/3
        Returns:
            list: list of markup urls referencing actual papers
        """

        self.driver.get(issue_url)
        time.sleep(2)  # Give the page time to load

        # Handle cookie popup only once, for the first request
        if not self.cookie_handled:
            self._handle_cookie_popup()
            self.cookie_handled = True

        # Scroll through the page to load all articles
        self._scroll_page()

        # Get the fully rendered HTML and pass it to BeautifulSoup
        html = self.driver.page_source
        soup = BeautifulSoup(html, "html.parser")

        # Now find all PDF links using the class_="UD_Listings_ArticlePDF"
        pdf_links = soup.find_all("a", class_="UD_Listings_ArticlePDF")
        pdf_links = [tag.get("href") for tag in pdf_links if tag.get("href")]
        base_url = "https://www.mdpi.com"
        pdf_links = [
            base_url + href if href.startswith("/") else href for href in pdf_links
        ]

        self.logger.info(f"  PDF links found: {len(pdf_links)}")
        return pdf_links

    def __call__(self, model: MDPIModel) -> Dict[int, Dict[int, List]]:
        def scrape_issue(volume_num: int, issue_num: int) -> List | None:
            issue_url = f"{model.journal_url}/{volume_num}/{issue_num}"
            self.logger.info(f"  Processing Issue URL: {issue_url}")
            try:
                # Get all PDF links using Selenium to scroll and handle cookie popup once
                pdf_links = self.scrape(issue_url)
                # If no PDF links are found, skip to the next volume
                if not pdf_links:
                    self.logger.info(
                        f"  No PDF links found for Issue {issue_num} in Volume {volume_num}. Skipping to the next volume."
                    )
                    return None
                return pdf_links
            except Exception as e:
                self.logger.error(
                    f"  Failed to process Issue {issue_num} in Volume {volume_num}. Error: {e}"
                )
                return None

        def scrape_volume(volume_num: int) -> Dict[int, List]:
            start_issue = model.start_issue
            end_issue = model.end_issue

            self.logger.info(f"\nProcessing Volume {volume_num}...")
            return {issue_num: sir for issue_num in range(start_issue, end_issue + 1) if (sir := scrape_issue(volume_num, issue_num))}

        start_volume = model.start_volume
        end_volume = model.end_volume

        # input: complete url with only journal
        # output: list complete url with journal and volume
        links = {volume_num: scrape_volume(volume_num) for volume_num in range(start_volume, end_volume + 1)}

        self.driver.quit()

        # TODO: save links in external file
        self._save_scraped_list(links)
        return links

    @property
    def name(self) -> str:
        return "mdpi"

    @property
    def model_class(self) -> Type[BaseModel]:
        return MDPIModel