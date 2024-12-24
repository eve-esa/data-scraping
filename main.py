from argparse import ArgumentParser
from dotenv import load_dotenv

from constants import CONFIG_PATH
from utils import read_json_file, discover_scrapers, run_scrapers


def main(args):
    scraper_config = read_json_file(CONFIG_PATH)
    scrapers = discover_scrapers("scrapers")

    if args.scrapers:
        scrapers = {name: scrapers[name] for name in args.scrapers}

    run_scrapers(scrapers, scraper_config)


if __name__ == "__main__":
    load_dotenv()

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
