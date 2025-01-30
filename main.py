from argparse import ArgumentParser
from dotenv import load_dotenv

from helper.constants import CONFIG_PATH
from helper.utils import read_json_file, discover_scrapers, run_scrapers
from service.database_manager import DatabaseManager
from service.resource_manager import Resource, ResourceManager


def main(args):
    # first of all, remove the scraping.log file
    with open("scraping.log", "w") as f:
        f.write("")

    scraper_config = read_json_file(CONFIG_PATH)
    scrapers = discover_scrapers("scraper")

    if args.scrapers:
        scrapers = {name: scrapers[name] for name in args.scrapers}

    run_scrapers(scrapers, scraper_config)


def init_db():
    database_manager = DatabaseManager()

    resource_manager = ResourceManager()
    resource_table = resource_manager.table_name
    database_manager.create_table(
        resource_table, {field: "TEXT" for field in Resource.model_fields.keys() if field != "id"}
    )


if __name__ == "__main__":
    load_dotenv()
    init_db()

    parser = ArgumentParser()
    parser.add_argument(
        '-s',
        "--scrapers",
        default=[],
        nargs="+",
        help="Run the scrapers identified in the list of names provided.",
    )

    args = parser.parse_args()

    main(args)
