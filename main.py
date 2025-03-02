import json
from argparse import ArgumentParser
from dotenv import load_dotenv

from helper.constants import CONFIG_PATH
from helper.database import init_db
from helper.utils import read_json_file, discover_scrapers, run_scrapers, resume_upload_scrapers
from service.analytics_manager import AnalyticsManager


def parse_arguments():
    parser = ArgumentParser()

    parser.add_argument(
        '-s',
        "--scrapers",
        default=[],
        nargs="+",
        help="Run the scrapers identified in the provided list of names.",
    )

    parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="Force scraping of all resources, regardless of the last time they were scraped.",
    )
    parser.add_argument(
        "-a",
        "--analytics-only",
        action="store_true",
        help="Only show analytics without running scrapers",
    )
    parser.add_argument(
        "-r",
        "--resume-upload",
        action="store_true",
        help="Resume uploading the data to the remote storage",
    )
    return parser.parse_args()


def main(args):
    scrapers = discover_scrapers()
    if args.scrapers:
        scrapers = {name: scrapers[name] for name in args.scrapers if name in scrapers}

    if not scrapers:
        print("No scraper found.")
        return

    if args.analytics_only:
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

    if args.resume_upload:
        resume_upload_scrapers(scrapers, scraper_config)
        return

    run_scrapers(scrapers, scraper_config, force=args.force)


if __name__ == "__main__":
    load_dotenv()
    init_db()

    main(parse_arguments())
