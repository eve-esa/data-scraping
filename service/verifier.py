from typing import Dict, Set
from service.storage import S3Storage

class ScrapingVerifier:
    def __init__(self, log_file: str = "scraping.log"):
        self.log_file = log_file
        self.s3_storage = S3Storage()

    def extract_uploads_from_logs(self) -> Dict[str, Set[str]]:
        """Extract successful uploads from logs by scraper."""
        scraper_uploads: Dict[str, Set[str]] = {}
        active_scrapers: Set[str] = set()
        
        with open(self.log_file, 'r') as f:
            for line in f:
                # Track when scrapers start
                if "INFO: Running scraper" in line:
                    scraper_name = line.split("Running scraper")[1].strip()
                    active_scrapers.add(scraper_name)
                    if scraper_name not in scraper_uploads:
                        scraper_uploads[scraper_name] = set()
                
                # Track when scrapers complete
                elif "INFO: Scraper" in line and "successfully completed" in line:
                    scraper_name = line.split("Scraper")[1].split("successfully")[0].strip()
                    active_scrapers.discard(scraper_name)
                
                # Track successful uploads
                elif "[service.storage] INFO: Successfully uploaded to S3:" in line:
                    s3_path = line.split("Successfully uploaded to S3:")[1].strip()
                    # Determine which scraper this belongs to based on the path
                    scraper_prefix = s3_path.split('/')[1].lower()  # e.g., 'jaxa', 'wikipedia'
                    
                    # Find the matching active scraper
                    for scraper in active_scrapers:
                        if scraper.lower().replace('scraper', '') in scraper_prefix:
                            if scraper not in scraper_uploads:
                                scraper_uploads[scraper] = set()
                            scraper_uploads[scraper].add(s3_path)
                            break

        return scraper_uploads

    def verify_s3_contents(self) -> Dict[str, Dict[str, any]]:
        """Verify if logged uploads match S3 bucket contents."""
        logged_uploads = self.extract_uploads_from_logs()
        verification_results = {}

        for scraper, uploads in logged_uploads.items():
            # Get the prefix for this scraper (e.g., 'raw_data/jaxa/')
            scraper_name = scraper.lower().replace('scraper', '')
            prefix = f"raw_data/{scraper_name}"
            s3_files = set(self.s3_storage.list_objects(prefix))

            missing_files = uploads - s3_files

            verification_results[scraper] = {
                "expected_count": len(uploads),
                "actual_count": len(s3_files),
                "missing_files": sorted(list(missing_files)),
                "matches": len(missing_files) == 0
            }

        return verification_results

    def run_verification(self) -> bool:
        """Run verification and return overall success status."""
        results = self.verify_s3_contents()
        return all(result["matches"] for result in results.values())
