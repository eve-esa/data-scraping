import importlib
import inspect
import json
import os
import pkgutil
import random
import time
from multiprocessing import Queue
import zipfile
from typing import Dict, List, Type, Tuple
import requests
import yaml
from bs4 import Tag
from urllib.parse import urlparse, parse_qs
from fake_useragent import UserAgent, FakeUserAgentError
from selenium.webdriver.remote.webelement import WebElement
from seleniumbase import SB
from seleniumbase.undetected.cdp_driver.element import Element
import filetype
import magic
import mimetypes

from helper.constants import DEFAULT_UA
from helper.logger import setup_logger
from helper.worker import setup_worker_logging, setup_workers
from model.analytics_models import AnalyticsModelItem, AnalyticsModelItemRatio, AnalyticsModelItemTotal
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


def get_file_extension_from_file_content(content: bytes) -> str | None:
    """
    Get the file extension from the content.

    Args:
        content (bytes): The content of the file.

    Returns:
        str: The file extension, or None if the extension cannot be determined.
    """
    kind = filetype.guess(content)
    if kind is None:
        mime = magic.Magic(mime=True)
        mime_type = mime.from_buffer(content)
        return (mimetypes.guess_extension(mime_type) or "").lstrip(".")

    return kind.extension


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
    def run_scraper_process(log_queue: Queue, class_type_scraper: Type[BaseScraper], config_scraper: Dict):
        setup_worker_logging(log_queue, logger_name)
        scraper_obj = class_type_scraper()
        scraper_obj.set_config_model_from_dict(config_scraper)
        scraper_obj(force=force)

    logger_name = __name__
    setup_workers(discovered_scrapers, config, run_scraper_process, logger_name, log_file)


def resume_upload_scrapers(
    discovered_scrapers: Dict[str, Type[BaseScraper]],
    config: Dict[str, Dict],
    log_file: str = "logs/scraping.log",
):
    """
    Resume the mentioned scrapers, so that the files can be (re-)uploaded to the remote storage. Run them in separate
    processes with configured logging.

    Args:
        discovered_scrapers (Dict[str, Type[BaseScraper]]): A dictionary of scraper names and their classes.
        config (Dict[str, Dict]): A dictionary of scraper names and their configurations.
        log_file (str): Path to the log file.
    """
    def run_resume_upload_process(log_queue: Queue, class_type_scraper: Type[BaseScraper], config_scraper: Dict):
        setup_worker_logging(log_queue, logger_name)
        scraper_obj = class_type_scraper()
        scraper_obj.set_config_model_from_dict(config_scraper)
        scraper_obj.resume_uploads()

    logger_name = __name__
    setup_workers(discovered_scrapers, config, run_resume_upload_process, logger_name, log_file)


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


def get_user_agent(include_mobile: bool = False) -> str:
    if _ua is None:
        return DEFAULT_UA

    random_ua = _ua.random
    if include_mobile:
        return random_ua

    while "mobile" in random_ua.lower():
        random_ua = _ua.random

    return random_ua


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

    return list(set(extracted_lists))


def build_analytics(successes: List[str], failures: List[str]) -> AnalyticsModelItem:
    """
    Build an analytics model item from the successes and failures.

    Args:
        successes (List[str]): A list of successful scrapes.
        failures (List[str]): A list of failed scrapes.

    Returns:
        AnalyticsModelItem: The analytics model item.
    """
    successes = list(set(successes))
    failures = list(set(failures))
    total = len(successes) + len(failures)

    totals = AnalyticsModelItemTotal(success=len(successes), failure=len(failures))
    ratios = AnalyticsModelItemRatio(
        success=len(successes) / total if total > 0 else 0,
        failure=len(failures) / total if total > 0 else 0,
    )

    return AnalyticsModelItem(
        success=successes,
        failure=failures,
        totals=totals,
        ratios=ratios,
    )


def get_bool_env(key: str, default: str) -> bool:
    v = os.getenv(key, default).lower()
    return v == "true" or v == "1"


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
    href = tag.get("href", getattr(tag, "href"))
    if href.startswith("http"):
        return href.strip()

    # Remove trailing/leading slashes except in http(s)://
    prefix = base_url.rstrip("/")
    if prefix.endswith(":"):
        prefix += "//"

    # Join with single slash
    result = f"{prefix}/{href.lstrip('/').strip()}"
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
    href = we.get_attribute("href") or getattr(we, "href")
    if href.startswith("http"):
        return href.strip()

    # Remove trailing/leading slashes except in http(s)://
    prefix = base_url.rstrip("/")
    if prefix.endswith(":"):
        prefix += "//"

    # Join with single slash
    result = f"{prefix}/{href.lstrip('/').strip()}"
    return result if with_querystring else remove_query_string_from_url(result)


def get_resource_from_remote_by_request(
    source_url: str, request_with_proxy: bool = False, max_retries: int | None = 5
) -> bytes:
    proxy = get_interacting_proxy_config()
    headers = {
        "User-Agent": get_user_agent(),
        "Accept": "application/pdf",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.google.com",
    }

    retry_count = 0
    while retry_count <= max_retries:
        if retry_count > 0:
            headers["Accept-Encoding"] = "identity"
        try:
            response = requests.get(
                source_url, headers=headers, proxies={"http": proxy, "https": proxy}, verify=False
            ) if request_with_proxy else requests.get(source_url, headers=headers)

            response.raise_for_status()  # Check for request errors

            return response.content
        except Exception as e:
            retry_count += 1
            if retry_count <= max_retries:
                time.sleep(2 * retry_count)
            else:
                raise e

    raise Exception(f"Failed to retrieve the content from {source_url}")


def get_resource_from_remote_by_scraping(
    source_url: str,
    loading_tag: str | None = None,
    cookie_selector: str | None = None,
    timeout: int | None = 10,
) -> bytes:
    # return the resource from the scraping if the loading tag is provided
    with SB(**get_sb_configuration()) as sb:
        sb.activate_cdp_mode(source_url)
        sb.maximize()
        sb.cdp.sleep(1)
        sb.uc_gui_click_captcha()

        # Wait for the page to load
        if loading_tag:
            sb.cdp.assert_element_absent(loading_tag, timeout=timeout)

        # Handle cookie popup
        if cookie_selector:
            try:
                sb.cdp.click(cookie_selector, timeout=timeout)
            except:
                pass

        # Sleep for some time to avoid being blocked by the server on the next request
        sb.cdp.sleep(random.uniform(2, 5))

        # Get the fully rendered HTML
        content = sb.cdp.get_page_source()
        return content.encode("utf-8")


def get_sb_configuration() -> Dict:
    return {
        "undetectable": True,
        "locale_code": "en",
        "headless2": get_bool_env("HEADLESS_BROWSER", "true"),
        "disable_cookies": False,
        "xvfb": get_bool_env("XVFB_MODE", "false"),
    }


def get_ancestor(tag: Element, selector: str) -> Element | None:
    if not tag or not selector:
        return None

    parts = selector.split(".")
    tag_name = None if selector.startswith(".") else parts[0]
    class_names = parts[1:] if "." in selector else []
    class_names = [class_name for class_name in class_names if class_name]

    condition = all([class_name in tag.class_ for class_name in class_names])
    if tag_name:
        condition = tag.tag_name == tag_name and condition

    if condition:
        return tag

    return get_ancestor(tag.get_parent(), selector) if tag.get_parent() else None
