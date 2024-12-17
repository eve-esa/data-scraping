import importlib
import inspect
import pkgutil
import threading
from typing import Dict
import yaml
import logging
from pydantic import ValidationError

from scrapers.base import BaseScraper

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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

        discovered_scrapers |= {
            name: obj()
            for name, obj in inspect.getmembers(module)
            if inspect.isclass(obj) and issubclass(obj, BaseScraper) and obj is not BaseScraper and hasattr(obj, "__call__")
        }

    logger.info(f"Discovered and started scrapers: {list(discovered_scrapers.keys())}")

    return discovered_scrapers


def run_scrapers(discovered_scrapers: Dict, config: Dict | None = None):
    """
    Find all scraper classes in the specified package and run them in separate threads.
    """

    def run_scraper(model_class, scraper_config):
        model_instance = model_class(**scraper_config) if model_class else None
        scraper(model_instance)

    threads = []
    for name, scraper in discovered_scrapers.items():
        try:
            thread = threading.Thread(
                target=run_scraper,
                args=(getattr(scraper, "model_class", None), config.get(name, {}) if config else {})
            )
            thread.start()
            threads.append(thread)
        except ValidationError as e:
            logger.error(f"Error running scraper {name}: {e}")

    for thread in threads:
        thread.join()
