from utils import read_json_file, discover_scrapers, run_scrapers

if __name__ == "__main__":
    config_file = "configs/scraper_config.json"

    scraper_config = read_json_file(config_file)
    scrapers = discover_scrapers("scrapers")

    run_scrapers(scrapers, scraper_config)
