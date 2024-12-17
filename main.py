from utils import read_yaml_file, setup_logging, discover_scrapers, run_scrapers

if __name__ == "__main__":
    setup_logging()

    scraper_config = read_yaml_file("configs/scraper_config.yaml")
    scrapers = discover_scrapers("scrapers")

    run_scrapers(scrapers, scraper_config)

