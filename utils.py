import importlib
import inspect
import logging
import os
import pkgutil
import threading
from typing import Dict

import yaml

from scrapers.base import BaseScraper


def setup_logging():
    with open(f"logs/logging.{os.getenv('ENV', 'dev')}.yml", "rt", encoding="utf-8") as f:
        try:
            logging.config.dictConfig(yaml.safe_load(f.read()))
        except Exception as e:
            print(e)
            print("Error in Logging Configuration. Using default configs")
            logging.basicConfig(level=logging.INFO)


# Load the YAML file
def read_yaml_file(file_path: str):
    with open(file_path, "r") as file:
        data = yaml.safe_load(file)
    return data


def discover_scrapers(base_package: str) -> Dict:
    """
    Find all scraper classes in the specified package and run them in separate threads.
    """
    package = importlib.import_module(base_package)

    discovered_scrapers = {}
    for _, module_name, _ in pkgutil.iter_modules(package.__path__):
        module = importlib.import_module(f"{base_package}.{module_name}")

        discovered_scrapers = {
            name: obj()
            for name, obj in inspect.getmembers(module)
            if inspect.isclass(obj) and issubclass(obj, BaseScraper) and obj is not BaseScraper and hasattr(obj, '__call__')
        }

    logging.info("Discovered and started scrapers:", discovered_scrapers)

    return discovered_scrapers


def run_scrapers(discovered_scrapers: Dict, config: Dict | None = None):
    """
    Find all scraper classes in the specified package and run them in separate threads.
    """

    def run_scraper(scraper_instance, model_class, scraper_config):
        model_instance = model_class(**scraper_config) if model_class else None
        scraper_instance(model_instance, scraper_config)

    threads = []
    for name, scraper in discovered_scrapers.items():
        thread = threading.Thread(
            target=run_scraper,
            args=(scraper, getattr(scraper, 'model_class', None), config.get(name.lower(), {}) if config else {})
        )
        thread.start()
        threads.append(thread)

    for thread in threads:
        thread.join()
