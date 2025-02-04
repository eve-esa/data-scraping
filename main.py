from argparse import ArgumentParser
from dotenv import load_dotenv

from helper.constants import CONFIG_PATH
from helper.database import init_db
from helper.utils import read_json_file, discover_scrapers, run_scrapers


def main(args):
    # first of all, remove the scraping.log file
    with open("scraping.log", "w") as f:
        f.write("")

    scraper_config = read_json_file(CONFIG_PATH)
    scrapers = discover_scrapers()

    if args.scrapers:
        scrapers = {name: scrapers[name] for name in args.scrapers}

    force_running = args.force
    run_scrapers(scrapers, scraper_config, force=force_running)


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

    parser.add_argument(
        "-f",
        "--force",
        default=False,
        help="Force scraping of all resources, regardless of the last time they were scraped.",
    )

    args = parser.parse_args()

    main(args)
