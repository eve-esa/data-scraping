import importlib
import inspect
import json
import os
import pkgutil
import threading
from typing import Dict, List, Type
import yaml
import logging
from bs4 import Tag
from pydantic import ValidationError
from urllib.parse import urlparse

from constants import OUTPUT_FOLDER
from scraper.base_scraper import BaseScraper

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
               and not inspect.isabstract(obj)
               and hasattr(obj, "scrape")
        }

    logger.info(f"Discovered and started scrapers: {list(discovered_scrapers.keys())}")

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
        is_done = os.path.exists(os.path.join(OUTPUT_FOLDER, f"{name_scraper}.json"))
        if is_done:
            logger.warning(f"Scraper {name_scraper} already done")
            continue

        config_scraper = config.get(name_scraper, None)
        if config_scraper is None:
            logger.error(f"Scraper {name_scraper} not found in configured scrapers")
            continue

        scraper_obj = class_type_scraper()
        config_model_type_scraper = getattr(scraper_obj, "config_model_type", None)
        if config_model_type_scraper is None:
            logger.error(f"Config class not found for scraper {name_scraper}")
            continue

        try:
            thread = threading.Thread(target=lambda: scraper_obj(config_model_type_scraper(**config_scraper)))
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
    return tag.get("href") if tag.get("href").startswith("http") else base_url + tag.get("href")


def get_pdf_name(pdf_url: str) -> str:
    """
    Get the PDF name from the URL.

    Args:
        pdf_url (str): The URL of the PDF.

    Returns:
        str: The name of the PDF.
    """
    parsed = urlparse(pdf_url)

    path = parsed.path.lstrip("/")
    # if the `path` contains `.pdf`, return the last part of the URL
    if ".pdf" in path:
        return path.split("/")[-1]

    # otherwise, replace `/` with `_` and add `.pdf`
    return path.replace("/", "_") + ".pdf"
