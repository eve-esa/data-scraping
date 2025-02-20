import importlib
import inspect
import json
import os
import pkgutil
import queue
import random
import shutil
from logging.handlers import QueueListener
from multiprocessing import Queue, Process
import zipfile
from typing import Dict, List, Type, Tuple
import requests
import yaml
from bs4 import Tag
from pydantic import ValidationError, BaseModel
from urllib.parse import urlparse, parse_qs
from fake_useragent import UserAgent, FakeUserAgentError
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.by import By
import time
from seleniumbase import SB
from seleniumbase.common.exceptions import NoSuchElementException, ElementNotVisibleException, TimeoutException

from helper.constants import DEFAULT_UA, DEFAULT_CRAWLING_FOLDER
from helper.logger import setup_logger, setup_worker_logging
from model.analytics_models import AnalyticsModelItem, AnalyticsModelItemPercentage, AnalyticsModelItemTotal
from scraper.base_scraper import BaseScraper, BaseMappedSubScraper


try:
    _ua = UserAgent()
except FakeUserAgentError:
    _ua = None


# Load the YAML file
def read_yaml_file(file_path: str):
    with open(file_path, "r") as file:
        data = yaml.safe_load(file)
    return data


# Write the YAML file
def write_yaml_file(file_path: str, data: Dict | List):
    with open(file_path, "w") as file:
        yaml.dump(data, file, default_flow_style=False)


# Load the JSON file
def read_json_file(file_path: str):
    with open(file_path, "r") as file:
        data = json.load(file)
    return data


# Write the JSON file
def write_json_file(file_path: str, data: Dict | List):
    # if the folder does not exist, create it
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    with open(file_path, "w") as file:
        json.dump(data, file, indent=4)


def is_json_serializable(data) -> bool:
    """
    Check if an object can be serialized to JSON
    """
    try:
        json.dumps(data)
        return True
    except (TypeError, ValueError):
        return False


def discover_scrapers(log_file: str = "logs/scraping.log") -> Dict[str, Type[BaseScraper]]:
    """
    Find all scraper classes in the specified package and run them in separate threads.

    Args:
        log_file (str): Path to the log file.

    Returns:
        Dict[str, BaseScraper]: A dictionary of scraper names and their classes (i.e., the type).
    """
    logger = setup_logger(__name__, log_file)
    base_package = "scraper"

    package = importlib.import_module(base_package)

    discovered_scrapers = {}
    for _, module_name, _ in pkgutil.iter_modules(package.__path__):
        module = importlib.import_module(f"{base_package}.{module_name}")

        discovered_scrapers |= {
            name: obj_type
            for name, obj_type in inspect.getmembers(module)
            if inspect.isclass(obj_type)
               and issubclass(obj_type, BaseScraper)
               and not issubclass(obj_type, BaseMappedSubScraper)
               and not inspect.isabstract(obj_type)
               and hasattr(obj_type, "scrape")
        }

    logger.debug(f"Discovered scrapers: {list(discovered_scrapers.keys())}")

    return discovered_scrapers


def run_scraper_process(
    scraper_obj: BaseScraper, config_model: BaseModel, log_queue: Queue, logger_name: str, force: bool = False
):
    """
    Wrapper function to run a scraper with logging configuration.

    Args:
        scraper_obj (BaseScraper): The scraper object to run.
        config_model (BaseModel): The configuration model for the scraper.
        log_queue (Queue): The logging queue.
        logger_name (str): The name of the logger.
        force (bool): Whether to force scraping of all resources.
    """
    setup_worker_logging(log_queue, logger_name)
    scraper_obj(config_model, force=force)


def run_scrapers(
    discovered_scrapers: Dict[str, Type[BaseScraper]],
    config: Dict[str, Dict],
    log_file: str = "logs/scraping.log",
    force: bool = False,
):
    """
    Find all scraper classes in the specified package and run them in separate processes with configured logging.

    Args:
        discovered_scrapers (Dict[str, Type[BaseScraper]]): A dictionary of scraper names and their classes.
        config (Dict[str, Dict]): A dictionary of scraper names and their configurations.
        log_file (str): Path to the log file.
        force (bool): Whether to force scraping of all resources.
    """
    # Create logging queue
    log_queue = Queue()

    # Setup main process logger
    logger = setup_logger(__name__, log_file)

    # Create and start listener
    listener = QueueListener(log_queue, *logger.handlers, respect_handler_level=True)
    listener.start()

    try:
        processes = []
        for name_scraper, class_type_scraper in discovered_scrapers.items():
            config_scraper = config.get(name_scraper)
            if config_scraper is None:
                logger.error(f"Scraper {name_scraper} not found in configured scrapers")
                continue

            scraper_obj = class_type_scraper()
            try:
                config_model = scraper_obj.config_model_type(**config_scraper)
                process = Process(
                    target=run_scraper_process,
                    args=(scraper_obj, config_model, log_queue, __name__, force),
                    name=name_scraper
                )
                process.start()
                time.sleep(0.5)
                processes.append(process)
            except ValidationError as e:
                logger.error(f"Error running scraper {name_scraper}: {e}")

        # Wait for all processes to complete
        for process in processes:
            process.join()
    finally:
        # Ensure the queue is empty before stopping
        while not log_queue.empty():
            try:
                record = log_queue.get_nowait()
                logger.handle(record)
            except queue.Empty:
                break

        listener.stop()
        # Small delay to ensure all logs are processed
        time.sleep(0.1)

        # remove the entire crawling folder, if it exists
        if os.path.exists(DEFAULT_CRAWLING_FOLDER):
            shutil.rmtree(DEFAULT_CRAWLING_FOLDER)


def remove_query_string_from_url(url: str | None = None) -> str | None:
    """
    Remove the query string from the URL.

    Args:
        url (str): The URL to process.

    Returns:
        str | None: The URL without the query string, or None if the URL is None.
    """
    if url is None:
        return None

    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"


def get_scraped_url_by_bs_tag(tag: Tag, base_url: str, with_querystring: bool | None = False) -> str:
    """
    Get the URL from the Tag.

    Args:
        tag (Tag): The BeautifulSoup tag.
        base_url (str): The base URL.
        with_querystring (bool): Whether to include the query string in the URL.

    Returns:
        List[str]: A list of URLs of the articles in the issue.
    """
    if tag.get("href").startswith("http"):
        return tag.get("href")

    # Remove trailing/leading slashes except in http(s)://
    prefix = base_url.rstrip("/")
    if prefix.endswith(":"):
        prefix += "//"

    # Join with single slash
    result = f"{prefix}/{tag.get('href').lstrip('/')}"
    return result if with_querystring else remove_query_string_from_url(result)


def get_scraped_url_by_web_element(we: WebElement, base_url: str, with_querystring: bool | None = False) -> str:
    """
    Get the URL from the Tag.

    Args:
        we (WebElement): The Selenium WebElement.
        base_url (str): The base URL.
        with_querystring (bool): Whether to include the query string in the URL.

    Returns:
        List[str]: A list of URLs of the articles in the issue.
    """
    if we.get_attribute("href").startswith("http"):
        return we.get_attribute("href")

    # Remove trailing/leading slashes except in http(s)://
    prefix = base_url.rstrip("/")
    if prefix.endswith(":"):
        prefix += "//"

    # Join with single slash
    result = f"{prefix}/{we.get_attribute('href').lstrip('/')}"
    return result if with_querystring else remove_query_string_from_url(result)


def get_unique(pdf_links: List[str]) -> List[str]:
    """
    Get the unique PDF links.

    Args:
        pdf_links (List[str]): A list of PDF links.

    Returns:
        List[str]: A list of unique PDF links.
    """
    return list(set(pdf_links))


def unpack_zip_files(directory: str) -> bool:
    """
    Unpack the ZIP files in the directory.

    Args:
        directory (str): The directory containing the ZIP files.
    """
    zip_files = [f for f in os.listdir(directory) if f.endswith(".zip")]
    if not zip_files:
        return False

    # Unpack the ZIP files
    for zip_file in zip_files:
        zip_file_path = os.path.join(directory, zip_file)
        # Unpack the ZIP file
        with zipfile.ZipFile(zip_file_path, "r") as zip_ref:
            zip_ref.extractall(directory)
        # Remove the ZIP file
        os.remove(zip_file_path)
    return True


def get_link_for_accessible_article(article_tag: WebElement, base_url: str, xpath: str) -> str | None:

    """
    Check if the article is accessible (i.e., not behind a paywall) and return the URL. The method checks if the
    article tag has a lock-open icon, which indicates that the article is not behind a paywall. If the article is
    accessible, return the URL to the article. Otherwise, return None.

    Args:
        article_tag (WebElement): The article tag.
        base_url (str): The base URL of the publisher.
        xpath (str): The XPath to the element to check.

    Returns:
        str | None: The URL to the article if it is accessible, otherwise None.
    """
    try:
        article_tag.find_element(By.XPATH, xpath)
        return get_scraped_url_by_web_element(article_tag, base_url)
    except NoSuchElementException:
        return None


def get_user_agent(include_mobile: bool = False) -> str:
    if _ua is None:
        return DEFAULT_UA

    random_ua = _ua.random
    if include_mobile:
        return random_ua

    while "mobile" in random_ua.lower():
        random_ua = _ua.random

    return random_ua


def get_static_proxy_config() -> str:
    """
    This method integrates an external provider of proxy service. It returns a string with the proxy configuration. It
    returns a string with the configuration to pass to Selenium or Scrapy.

    Returns:
        str: The proxy configuration.
    """
    return f"{os.getenv('STATIC_PROXY_USER')}:{os.getenv('STATIC_PROXY_PASSWORD')}@{os.getenv('STATIC_PROXY_HOST')}:{os.getenv('STATIC_PROXY_PORT')}"


def get_interacting_proxy_config() -> str:
    """
    This method integrates an external provider of proxy service able to interact with the browser (no navigation). It
    returns a string with the configuration to pass to the HTTP requests.

    Returns:
        str: The web unlocker configuration.
    """
    return f"{os.getenv('INTERACTING_PROXY_USER')}:{os.getenv('INTERACTING_PROXY_PASSWORD')}@{os.getenv('INTERACTING_PROXY_HOST')}:{os.getenv('INTERACTING_PROXY_PORT')}"


def parse_google_drive_link(google_drive_link: str) -> Tuple[str, str]:
    """
    Extract the ID and download URL from the Google Drive link.

    Args:
        google_drive_link (str): The Google Drive link.

    Returns:
        Tuple[str, str]: The ID and download URL of the file.
    """
    parsed_url = urlparse(google_drive_link)
    parsed_query = parse_qs(parsed_url.query)
    file_id = parsed_url.path.split("/")[-2]
    if "d" in parsed_query:
        file_id = parsed_query["d"][0]
    if "id" in parsed_query:
        file_id = parsed_query["id"][0]

    # direct URL for the download
    download_url = f"https://drive.google.com/uc?id={file_id}"

    return file_id, download_url


def get_resource_from_remote_by_request(source_url: str, request_with_proxy: bool = False) -> bytes:
    proxy = get_interacting_proxy_config()
    headers = {
        "User-Agent": get_user_agent(),
        "Accept": "application/pdf",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.google.com",
    }

    response = requests.get(
        source_url, headers=headers, proxies={"http": proxy, "https": proxy}, verify=False
    ) if request_with_proxy else requests.get(source_url, headers=headers)

    response.raise_for_status()  # Check for request errors
    return response.content


def get_resource_from_remote_by_scraping(
    source_url: str,
    loading_tag: str | None = None,
    cookie_selector: str | None = None,
    timeout: int | None = 20,
) -> bytes:
    # return the resource from the scraping if the loading tag is provided
    with SB(**get_sb_configuration()) as sb:
        sb.activate_cdp_mode(source_url)
        sb.maximize()
        sb.sleep(1)
        sb.uc_gui_click_captcha()

        # Wait for the page to load
        if loading_tag:
            sb.cdp.assert_element_absent(loading_tag, timeout=timeout)

        # Handle cookie popup only once, for the first request
        if cookie_selector:
            try:
                sb.cdp.click(cookie_selector, timeout=timeout)
            except (TimeoutException, NoSuchElementException, ElementNotVisibleException):
                pass

        # Sleep for some time to avoid being blocked by the server on the next request
        sb.sleep(random.uniform(2, 5))

        # Get the fully rendered HTML
        content = sb.cdp.get_page_source()
        return content.encode("utf-8")


def extract_lists(input_data: List | Dict) -> List[str]:
    """
    Extracts all lists from an input that can be either a list or a nested dictionary.

    Args:
        input_data (list or dict): Input to process

    Returns:
        list: All lists found in the input
    """
    # If input is already a list, return it immediately
    if isinstance(input_data, list):
        return input_data

    # If input is not a dictionary, return empty list
    if not isinstance(input_data, dict):
        return []

    # List to collect all found lists
    extracted_lists = []

    # Iterate through all dictionary values
    for value in input_data.values():
        # If value is a list, add it
        if isinstance(value, list):
            extracted_lists.extend(value)
        # If value is a dictionary, call function recursively
        elif isinstance(value, dict):
            extracted_lists.extend(extract_lists(value))
        # If value is a list of dictionaries, process each dictionary
        elif isinstance(value, list) and all(isinstance(item, dict) for item in value):
            for item in value:
                extracted_lists.extend(extract_lists(item))

    return get_unique(extracted_lists)


def build_analytics(successes: List[str], failures: List[str]) -> AnalyticsModelItem:
    """
    Build an analytics model item from the successes and failures.

    Args:
        successes (List[str]): A list of successful scrapes.
        failures (List[str]): A list of failed scrapes.

    Returns:
        AnalyticsModelItem: The analytics model item.
    """
    successes = get_unique(successes)
    failures = get_unique(failures)
    total = len(successes) + len(failures)

    totals = AnalyticsModelItemTotal(success=len(successes), failure=len(failures))
    percentages = AnalyticsModelItemPercentage(
        success=len(successes) / total if total > 0 else 0,
        failure=len(failures) / total if total > 0 else 0,
    )

    return AnalyticsModelItem(
        success=successes,
        failure=failures,
        totals=totals,
        percentages=percentages,
    )


def get_bool_env(key: str, default: str) -> bool:
    v = os.getenv(key, default).lower()
    return v == "true" or v == "1"


def get_sb_configuration() -> Dict:
    return {
        "undetectable": True,
        "locale_code": "en",
        "headless2": get_bool_env("HEADLESS_BROWSER", "true"),
        "disable_cookies": False,
        "xvfb": get_bool_env("XVFB_MODE", "false"),
    }
