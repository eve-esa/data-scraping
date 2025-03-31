import json
from argparse import ArgumentParser
from dotenv import load_dotenv

from helper.constants import CONFIG_PATH
from helper.database import init_db
from helper.utils import read_json_file, discover_scrapers, run_scrapers, resume_upload_scrapers, resume_scrapers
from service.analytics_manager import AnalyticsManager


def parse_arguments():
    parser = ArgumentParser()

    parser.add_argument(
        "-d",
        "--database-only",
        action="store_true",
        help="Initialize the database only.",
    )

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
        "-u",
        "--resume-upload",
        action="store_true",
        help="Resume uploading the data to the remote storage",
    )
    parser.add_argument(
        "-r",
        "--resume",
        action="store_true",
        help="Resume the failed resources",
    )
    return parser.parse_args()


def main(args):
    init_db()

    if args.database_only:
        print("Database initialized.")
        return

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

    if args.resume_upload and args.resume:
        print("Cannot use both --resume-upload and --resume at the same time.")
        return

    # first of all, remove the scraping.log file
    with open("logs/scraping.log", "w") as f:
        f.write("")
    scraper_config = read_json_file(CONFIG_PATH)

    if args.resume_upload:
        resume_upload_scrapers(scrapers, scraper_config)
        return

    if args.resume:
        resume_scrapers(scrapers, scraper_config)
        return

    run_scrapers(scrapers, scraper_config, force=args.force)


if __name__ == "__main__":
    load_dotenv()
    main(parse_arguments())
