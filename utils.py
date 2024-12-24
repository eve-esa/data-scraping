import importlib
import inspect
import json
import os
import pkgutil
import threading
from typing import Dict, List, Callable
import yaml
import logging
from bs4 import BeautifulSoup
from pydantic import ValidationError

from constants import OUTPUT_FOLDER
from scrapers.base_scraper import BaseScraper

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


def discover_scrapers(base_package: str) -> Dict[str, BaseScraper]:
    """
    Find all scraper classes in the specified package and run them in separate threads.
    """
    package = importlib.import_module(base_package)

    discovered_scrapers = {}
    for _, module_name, _ in pkgutil.iter_modules(package.__path__):
        module = importlib.import_module(f"{base_package}.{module_name}")

        discovered_scrapers |= {
            name: obj()
            for name, obj in inspect.getmembers(module)
            if inspect.isclass(obj)
               and issubclass(obj, BaseScraper)
               and not inspect.isabstract(obj)
               and hasattr(obj, "scrape")
        }

    logger.info(f"Discovered and started scrapers: {list(discovered_scrapers.keys())}")

    return discovered_scrapers


def run_scrapers(discovered_scrapers: Dict[str, BaseScraper], config: Dict):
    """
    Find all scraper classes in the specified package and run them in separate threads.
    """
    threads = []
    for name_scraper, config_scraper in config.items():
        is_done = os.path.exists(os.path.join(OUTPUT_FOLDER, f"{name_scraper}.json"))
        if is_done:
            logger.warning(f"Scraper {name_scraper} already done")
            continue

        if name_scraper not in discovered_scrapers:
            logger.error(f"Scraper {name_scraper} not found in discovered scrapers")
            continue

        class_type_scraper = discovered_scrapers[name_scraper]  # e.g. SeosScraper
        config_model_type_scraper = getattr(class_type_scraper, "config_model_type", None)
        if config_model_type_scraper is None:
            logger.error(f"Config class not found for scraper {name_scraper}")
            continue

        try:
            thread = threading.Thread(target=lambda: class_type_scraper(config_model_type_scraper(**config_scraper)))
            thread.start()
            threads.append(thread)
        except ValidationError as e:
            logger.error(f"Error running scraper {name_scraper}: {e}")

    for thread in threads:
        thread.join()


def get_scraped_urls(scraper: BeautifulSoup, base_url: str, href: bool | Callable, class_: str | None = None) -> List[str]:
    """
    Get the URLs of the articles in the issue.

    Args:
        scraper (BeautifulSoup): The BeautifulSoup object.
        base_url (str): The base URL.
        href (bool | callable): The href attribute.
        class_ (str | None): The class attribute.

    Returns:
        List[str]: A list of URLs of the articles in the issue.
    """
    tags = scraper.find_all("a", class_=class_, href=href)
    return [base_url + tag.get("href") if tag.get("href").startswith("/") else tag.get("href") for tag in tags]
