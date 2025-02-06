from argparse import ArgumentParser
from dotenv import load_dotenv

from helper.constants import CONFIG_PATH
from helper.database import init_db
from helper.utils import read_json_file, discover_scrapers, run_scrapers

from service.analytics_manager import AnalyticsManager


def main(args):
    scrapers = discover_scrapers()
    analytics_only = args.analytics_only
    if analytics_only is None:
        analytics_only = True
    elif isinstance(analytics_only, str):
        analytics_only = analytics_only.lower() == "true" or analytics_only.lower() == "1"

    if not analytics_only:
        # first of all, remove the scraping.log file
        with open("scraping.log", "w") as f:
            f.write("")

        scraper_config = read_json_file(CONFIG_PATH)
        if args.scrapers:
            scrapers = {name: scrapers[name] for name in args.scrapers if name in scrapers}

        force_running = args.force
        run_scrapers(scrapers, scraper_config, force=force_running)

    analytics = AnalyticsManager()
    all_stats = analytics.get_all_analytics(list(scrapers.keys()))
    print(all_stats)


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

    parser.add_argument(
        "-a",
        "--analytics-only",
        default=False,
        nargs="?",
        help="Only show analytics without running scrapers",
    )

    args = parser.parse_args()

    main(args)
