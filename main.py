from argparse import ArgumentParser
from dotenv import load_dotenv

from helper.constants import CONFIG_PATH
from helper.utils import read_json_file, discover_scrapers, run_scrapers
from service.verifier import ScrapingVerifier

import datetime

def main(args):
    # first of all, remove the scraping.log file
    with open("scraping.log", "w") as f:
        f.write("")

    scraper_config = read_json_file(CONFIG_PATH)
    scrapers = discover_scrapers("scraper")

    if args.scrapers:
        scrapers = {name: scrapers[name] for name in args.scrapers}

    run_scrapers(scrapers, scraper_config)

    verifier = ScrapingVerifier()
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    with open("verification.log", "a") as f:
        f.write(f"\n{'='*50}\n")
        f.write(f"Verification Results - {timestamp}\n")
        f.write(f"{'='*50}\n")
        
        results = verifier.verify_s3_contents()
        for scraper, result in results.items():
            f.write(f"\nScraper: {scraper}\n")
            f.write(f"Expected files: {result['expected_count']}\n")
            f.write(f"Found files: {result['actual_count']}\n")
            
            if not result['matches']:
                if result['missing_files']:
                    f.write(f"Missing files ({len(result['missing_files'])}):\n")
                    for file in result['missing_files']:
                        f.write(f"  - {file}\n")
            else:
                f.write("✓ All files verified successfully\n")


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
