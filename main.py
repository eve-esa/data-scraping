from dotenv import load_dotenv

from constants import CONFIG_PATH
from utils import read_json_file, discover_scrapers, run_scrapers

if __name__ == "__main__":
    load_dotenv()

    scraper_config = read_json_file(CONFIG_PATH)
    scrapers = discover_scrapers("scrapers")

    run_scrapers(scrapers, scraper_config)
