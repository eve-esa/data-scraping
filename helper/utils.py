import importlib
import inspect
import json
import os
import pkgutil
import threading
import zipfile
from typing import Dict, List, Type
import yaml
import logging
from bs4 import Tag
from pydantic import ValidationError
from urllib.parse import urlparse
import undetected_chromedriver as uc
from fake_useragent import UserAgent

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
            name: obj
            for name, obj in inspect.getmembers(module)
            if inspect.isclass(obj)
               and issubclass(obj, BaseScraper)
               and not issubclass(obj, BaseMappedScraper)
               and not inspect.isabstract(obj)
               and hasattr(obj, "scrape")
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
    threads = []
    for name_scraper, class_type_scraper in discovered_scrapers.items():
        config_scraper = config.get(name_scraper)
        if config_scraper is None:
            logger.error(f"Scraper {name_scraper} not found in configured scrapers")
            continue

        scraper_obj = class_type_scraper()
        config_model = scraper_obj.config_model_type(**config_scraper)
        try:
            thread = threading.Thread(target=lambda: scraper_obj(config_model))
            thread.start()
            threads.append(thread)
        except ValidationError as e:
            logger.error(f"Error running scraper {name_scraper}: {e}")

    for thread in threads:
        thread.join()


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
    return f"{prefix}/{tag.get('href').lstrip('/')}"


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


def get_chrome_options() -> uc.ChromeOptions:
    chrome_options = uc.ChromeOptions()

    # Basic configuration
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument(f"--user-agent={UserAgent().random}")
    chrome_options.add_argument("--headless=new")  # Run in headless mode (no browser UI)
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--start-maximized')

    # Performance options
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    # Cookies and security
    chrome_options.add_argument("--enable-cookies")
    chrome_options.add_argument("--disable-web-security")
    chrome_options.add_argument("--ignore-certificate-errors")

    return chrome_options


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
