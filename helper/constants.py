import os
from typing_extensions import Final

CONFIG_PATH: Final[str] = os.path.join("config", "config.json")
DEFAULT_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
DEFAULT_CRAWLING_FOLDER = os.path.join(os.getcwd(), "crawled")
