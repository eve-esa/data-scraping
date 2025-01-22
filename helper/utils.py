import importlib
import inspect
import json
import os
import pkgutil
from multiprocessing import Process
import zipfile
from typing import Dict, List, Type, Tuple
import yaml
import logging
from bs4 import Tag
from pydantic import ValidationError
from urllib.parse import urlparse, parse_qs
from fake_useragent import UserAgent
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.by import By
from selenium.common import NoSuchElementException

from scraper.base_scraper import BaseScraper, BaseMappedScraper

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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


def discover_scrapers(base_package: str) -> Dict[str, Type[BaseScraper]]:
    """
    Find all scraper classes in the specified package and run them in separate threads.

    Args:
        base_package (str): The base package to search for scrapers.

    Returns:
        Dict[str, BaseScraper]: A dictionary of scraper names and their classes (i.e., the type).
    """
    package = importlib.import_module(base_package)

    discovered_scrapers = {}
    for _, module_name, _ in pkgutil.iter_modules(package.__path__):
        module = importlib.import_module(f"{base_package}.{module_name}")

        discovered_scrapers |= {
            name: obj_type
            for name, obj_type in inspect.getmembers(module)
            if inspect.isclass(obj_type)
               and issubclass(obj_type, BaseScraper)
               and not issubclass(obj_type, BaseMappedScraper)
               and not inspect.isabstract(obj_type)
               and hasattr(obj_type, "scrape")
        }

    logger.info(f"Discovered scrapers: {list(discovered_scrapers.keys())}")

    return discovered_scrapers


def run_scrapers(discovered_scrapers: Dict[str, Type[BaseScraper]], config: Dict[str, Dict]):
    """
    Find all scraper classes in the specified package and run them in separate threads.

    Args:
        discovered_scrapers (Dict[str, Type[BaseScraper]]): A dictionary of scraper names and their classes (i.e., types).
        config (Dict[str, Dict]): A dictionary of scraper names and their configurations.
    """
    processes = []
    for name_scraper, class_type_scraper in discovered_scrapers.items():
        config_scraper = config.get(name_scraper)
        if config_scraper is None:
            logger.error(f"Scraper {name_scraper} not found in configured scrapers")
            continue

        scraper_obj = class_type_scraper()
        config_model = scraper_obj.config_model_type(**config_scraper)
        try:
            process = Process(target=lambda: scraper_obj(config_model))
            process.start()
            processes.append(process)
        except ValidationError as e:
            logger.error(f"Error running scraper {name_scraper}: {e}")

    for process in processes:
        process.join()


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


def get_scraped_url(tag: Tag, base_url: str) -> str:
    """
    Get the URL from the Tag.

    Args:
        tag (Tag): The BeautifulSoup tag.
        base_url (str): The base URL.

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
    return remove_query_string_from_url(f"{prefix}/{tag.get('href').lstrip('/')}")


def get_filename(url: str, file_extension: str) -> str:
    """
    Get the filename from the URL.

    Args:
        url (str): The URL of the file.
        file_extension (str): The type of the file.

    Returns:
        str: The final name of the file.
    """
    parsed = urlparse(url)

    path = parsed.path.lstrip("/")
    # if the `path` contains the file extension, return the last part of the URL
    if file_extension in path:
        return path.split("/")[-1]

    # otherwise, replace `/` with `_` and add the file extension
    return path.replace("/", "_") + file_extension


def get_unique(pdf_links: List[str]) -> List[str]:
    """
    Get the unique PDF links.

    Args:
        pdf_links (List[str]): A list of PDF links.

    Returns:
        List[str]: A list of unique PDF links.
    """
    return list(set(pdf_links))


def unpack_zip_files(directory: str):
    """
    Unpack the ZIP files in the directory.

    Args:
        directory (str): The directory containing the ZIP files.
    """
    zip_files = [f for f in os.listdir(directory) if f.endswith(".zip")]
    if not zip_files:
        return

    # Unpack the ZIP files
    for zip_file in zip_files:
        zip_file_path = os.path.join(directory, zip_file)
        # Unpack the ZIP file
        with zipfile.ZipFile(zip_file_path, "r") as zip_ref:
            zip_ref.extractall(directory)
        # Remove the ZIP file
        os.remove(zip_file_path)


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
        return get_scraped_url(Tag(name="a", attrs={"href": article_tag.get_attribute("href")}), base_url)
    except NoSuchElementException:
        return None


def get_user_agent(include_mobile: bool = False) -> str:
    ua = UserAgent()
    random_ua = ua.random
    if include_mobile:
        return random_ua

    while "mobile" in random_ua.lower():
        random_ua = ua.random

    return random_ua


def get_random_proxy() -> str:
    """
    This method integrates Bright Data's proxy service with the requests library. It returns a dictionary with the
    proxy configuration. The proxy is a residential proxy that rotates the IP address for each request.

    Returns:
        str: The proxy configuration.
    """
    return f"http://{os.getenv('BRIGHTDATA_USERNAME')}:{os.getenv('BRIGHTDATA_PASSWORD')}@{os.getenv('BRIGHTDATA_PROXY')}"


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
