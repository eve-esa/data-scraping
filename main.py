import os
from scraper import MDPIScraper, IOPScraper
from utils import read_yaml_file

if __name__ == "__main__":

    scraper_config_path = "configs/scraper_config.yaml"
    scraper_config = read_yaml_file(scraper_config_path)

    mdpi_scaper = MDPIScraper()
    iop_scraper = IOPScraper()

    for publisher, details in scraper_config.get("publishers", {}).items():
        if publisher == "mdpi":
            for journal in details.get("journals", []):
                url = journal.get("url")
                issn = journal.get("ISSN")
                journal_url = os.path.join(url.rsplit("/", 2)[0], issn)
                start_volume = journal.get("volume_range").get("start")
                end_volume = journal.get("volume_range").get("end")
                start_issue = journal.get("issue_range").get("start")
                end_issue = journal.get("issue_range").get("end")
                print(journal_url)

                res = mdpi_scaper(
                    journal_url=journal_url,
                    start_volume=start_volume,
                    end_volume=end_volume,
                    start_issue=start_issue,
                    end_issue=end_issue,
                )

                print(res)
