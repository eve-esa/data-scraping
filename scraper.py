"""
    utils:
    retry_request
    download_pdfs
"""

import time
import logging
import os
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from abc import ABC, abstractmethod


class BaseScraper(ABC):
    """
    input:
    output: list of links to download

    steps:
    0) setup_selenium
    1) scroll_page
    2) handle_coockie

    override
    4) get_all_pdf_links_selenium

    Inherit:
    - MDPIPdfScraperCategory2
    - ArxivPdfScraperCategory3
    - SourceHTMLScraperCategory2
    -
    """

    def __init__(self) -> None:
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
        #driver = webdriver.Chrome(service=Service())
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
        try:
            # Locate and click the "Allow All" button on the cookie popup
            cookie_button = self.driver.find_element(
                By.XPATH,
                '//*[@id="CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll"]',
            )
            cookie_button.click()
            logging.info("Cookie popup accepted.")
        except Exception as e:
            logging.error("No cookie popup found or unable to click. Skipping...")
            pass

    @abstractmethod
    def get_url_list() -> list:
        pass

class MDPIScraper(BaseScraper):
    def __init__(self) -> None:
        super().__init__()
        self.cookie_handled = False

    # get paper url list from issue
    def get_url_list(self, issue_url: str) -> list:
        """_summary_

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
        logging.info(f"  PDF links found: {len(pdf_links)}")

        return pdf_links

    def get_url_list_from_journal(
        self, 
        #issue_url: str,
        start_volume: int,
        end_volume: int,
        start_issue: int,
        end_issue: int) -> list:
        # input: complete url with only journal
        # output: list omplete url with journal and volume
        # TODO Append pdf links of each volume/issue in a key value dict/nested list
        links = []
        for volume_num in range(start_volume, end_volume + 1):
            print(f"\nProcessing Volume {volume_num}...")

            start_issue = 1
            end_issue = 30  # Adjust based on the number of issues per volume

            for issue_num in range(start_issue, end_issue + 1):
                issue_url = f"https://www.mdpi.com/2072-4292/{volume_num}/{issue_num}"
                print(f"  Processing Issue URL: {issue_url}")

                try:
                    # Get all PDF links using Selenium to scroll and handle cookie popup once
                    pdf_links = self.get_url_list(issue_url)
                    print(pdf_links)
                    links.append(pdf_links)
                    # If no PDF links are found, skip to the next volume
                    if not pdf_links:
                        print(f"  No PDF links found for Issue {issue_num} in Volume {volume_num}. Skipping to the next volume.")
                        break  # Skip to the next volume

                except Exception as e:
                    print(f"  Failed to process Issue {issue_num} in Volume {volume_num}. Error: {e}")
        self.driver.quit()
        return 
    
class IOPScraper(BaseScraper):
    def __init__(self) -> None:
        super().__init__()
        self.cookie_handled = False

    # get paper url list from issue
    def get_url_list(self, issue_url: str) -> list:
        """_summary_

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
        print(f"PDF links found: {len(pdf_links)}")

        return pdf_links

class SpringerScraper(BaseScraper):
    #TODO
    def __init__(self) -> None:
        super().__init__()
        self.cookie_handled = False
    pass

if __name__ == "__main__":
    mdpi_scaper = MDPIScraper()
    #issue_url = "https://www.mdpi.com/2072-4292/1/3"
    #urls = mdpi_scaper.get_url_list(issue_url=issue_url)
    #paper_urls = mdpi_scaper.get_url_list_from_journal(start_volume=1, end_volume=2, start_issue=1, end_issue=30)
    iop_scraper = IOPScraper()
    iop_url = "https://iopscience.iop.org/issue/1755-1315/37/1"
    iop_urls = iop_scraper.get_url_list(iop_url)
    print(iop_urls)
