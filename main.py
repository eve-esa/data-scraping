import json
from argparse import ArgumentParser
from dotenv import load_dotenv

from helper.constants import CONFIG_PATH
from helper.database import init_db
from helper.utils import read_json_file, discover_scrapers, run_scrapers

from service.analytics_manager import AnalyticsManager


def main(args):
    def parse_bool_arg(arg) -> bool:
        if arg is None:
            arg = True
        elif isinstance(arg, str):
            arg = arg.lower() == "true" or arg.lower() == "1"
        return arg

    scrapers = discover_scrapers()
    if args.scrapers:
        scrapers = {name: scrapers[name] for name in args.scrapers if name in scrapers}

    if parse_bool_arg(args.analytics_only):
        analytics_manager = AnalyticsManager()
        print(json.dumps(
            analytics_manager.find_multiple_latest_analytics(list(scrapers.keys()), as_dict=True),
            sort_keys=True,
            indent=4
        ))
        return

    # first of all, remove the scraping.log file
    with open("logs/scraping.log", "w") as f:
        f.write("")
    scraper_config = read_json_file(CONFIG_PATH)
    run_scrapers(scrapers, scraper_config, force=parse_bool_arg(args.force))


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
        nargs="?",
        help="Force scraping of all resources, regardless of the last time they were scraped.",
    )

    parser.add_argument(
        "-a",
        "--analytics-only",
        default=False,
        nargs="?",
        help="Only show analytics without running scrapers",
    )

    args = parser.parse_args()

    main(args)
