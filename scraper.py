import time
import logging
import os
import json
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.wait import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from abc import ABC, abstractmethod

from utils import setup_logging, read_yaml_file

#setup_logging()

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    _output_file = "configs/scraper_config.yaml"

    def __init__(self, config_file: str = "configs/scraper_config.yaml") -> None:
        self.driver = self._setup_selenium()

    def _setup_selenium(self):
        chrome_options = Options()
        chrome_options.add_argument(
            "--headless"
        )  # Run in headless mode (no browser UI)
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")

        # Create a new Chrome browser instance
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()), options=chrome_options
        )
        # driver = webdriver.Chrome(service=Service())
        return driver

    def _scroll_page(self, pause_time: int = 2):
        last_height = self.driver.execute_script("return document.body.scrollHeight")

        while True:
            # Scroll down to the bottom
            self.driver.execute_script(
                "window.scrollTo(0, document.body.scrollHeight);"
            )
            time.sleep(pause_time)

            # Calculate new scroll height and compare with the last height
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

    def _handle_cookie_popup(self):
        """Handle the cookie popup by interacting with the 'Accept All' button using JavaScript."""
        try:
            # Wait for the page to fully load
            WebDriverWait(self.driver, 15).until(lambda d: d.execute_script("return document.readyState") == "complete")
            logger.info("Page fully loaded. Attempting to locate the 'Accept All' button using JavaScript.")

            # Execute JavaScript to find and click the "Accept All" button
            self.driver.execute_script("""
                let acceptButton = document.querySelector("body > div.cky-consent-container.cky-classic-bottom > div.cky-consent-bar > div > div > div.cky-notice-btn-wrapper > button.cky-btn.cky-btn-accept");
                if (acceptButton) {
                    acceptButton.click();
                }
            """)
            logger.info("'Accept All' button clicked successfully using JavaScript.")
        except Exception as e:
            logger.error(f"Failed to handle cookie popup using JavaScript. Error: {e}")

    @abstractmethod
    def get_url_list() -> list:
        pass


# TODO: save links in external file
class MDPIScraper(BaseScraper):
    def __init__(self) -> None:
        super().__init__()
        self.cookie_handled = False

    # get paper url list from issue
    def get_url_list(self, issue_url: str) -> list:
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

        logging.info(f"  PDF links found: {len(pdf_links)}")
        return pdf_links

    def __call__(
        self,
        journal_url: str,
        start_volume: int = 1,
        end_volume: int = 16,
        start_issue: int = 1,
        end_issue: int = 30,
    ) -> list:
        # input: complete url with only journal
        # output: list omplete url with journal and volume
        # TODO Append pdf links of each volume/issue in a key value dict/nested list
        links = []
        for volume_num in range(start_volume, end_volume + 1):
            logging.info(f"\nProcessing Volume {volume_num}...")

            for issue_num in range(start_issue, end_issue + 1):
                issue_url = f"{journal_url}/{volume_num}/{issue_num}"
                logging.info(f"  Processing Issue URL: {issue_url}")

                try:
                    # Get all PDF links using Selenium to scroll and handle cookie popup once
                    pdf_links = self.get_url_list(issue_url)
                    links.extend(pdf_links)
                    # If no PDF links are found, skip to the next volume
                    if not pdf_links:
                        logging.info(
                            f"  No PDF links found for Issue {issue_num} in Volume {volume_num}. Skipping to the next volume."
                        )
                        break  # Skip to the next volume

                except Exception as e:
                    logging.error(
                        f"  Failed to process Issue {issue_num} in Volume {volume_num}. Error: {e}"
                    )
        self.driver.quit()
        self._save_scraped_list(links)
        return links


# TODO: popoup automation not working
class IOPScraper(BaseScraper):
    """This class acts only on issues urls, because those are the only once identified in the data_collection gsheet"""

    def __init__(self) -> None:
        super().__init__()
        self.cookie_handled = False

    def __call__(self, issue_url: str) -> list:
        return self.get_url_list(issue_url)

    # get paper url list from issue
    def get_url_list(self, issue_url: str) -> list:
        """get a list of url

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

        # Find all PDF links using appropriate class or tag
        pdf_links = soup.find_all("a", href=lambda href: href and "/article/" in href)
        logging.info(f"PDF links found: {len(pdf_links)}")

        return pdf_links


class SpringerScraper(BaseScraper):
    # TODO
    def __init__(self) -> None:
        super().__init__()
        self.cookie_handled = False

    pass


if __name__ == "__main__":
    mdpi_scaper = MDPIScraper()
    iop_scraper = IOPScraper()

    # get these urls from data collection gsheet
    # iop_url = "https://iopscience.iop.org/issue/1755-1315/540/1"
    mdpi_url = "https://www.mdpi.com/2072-4292"

    # print(iop_scraper(iop_url))
    print(mdpi_scaper(mdpi_url))
