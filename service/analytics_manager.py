from typing import Dict
from helper.singleton import singleton
from sqlalchemy import text
from .database_manager import DatabaseManager
import json

@singleton
class AnalyticsManager:
    def __init__(self):
        self.db = DatabaseManager()
        
    def get_scraper_success_failure_rates(self) -> Dict[str, Dict[str, float]]:
        """Calculate scraper success and failure rates"""
        with self.db.engine.connect() as connection:
            # Get all scraper outputs and failures
            outputs = connection.execute(text("SELECT scraper, output FROM scraper_outputs")).fetchall()
            failures = connection.execute(text("SELECT * FROM scraper_failures")).fetchall()
            
            # Process scraper outputs to count total URLs per scraper
            scraper_totals = {}
            for output in outputs:
                scraper_name = output[0]
                try:
                    urls = json.loads(output[1])
                    scraper_totals[scraper_name] = scraper_totals.get(scraper_name, 0) + len(urls)
                except json.JSONDecodeError:
                    continue
            
            # Count failures per scraper
            failure_counts = {}
            for failure in failures:
                scraper_name = failure[1]
                if scraper_name:
                    failure_counts[scraper_name] = failure_counts.get(scraper_name, 0) + 1
            
            # Calculate success and failure rates
            scraper_rates = {}
            for scraper in set(scraper_totals.keys()) | set(failure_counts.keys()):
                total = scraper_totals.get(scraper, 0)
                failure_count = failure_counts.get(scraper, 0)
                
                if total > 0:
                    failure_percentage = (failure_count / total) * 100
                    success_percentage = 100.0 - failure_percentage
                    scraper_rates[scraper] = {
                        "success": round(success_percentage, 2),
                        "failure": round(failure_percentage, 2)
                    }
                elif failure_count > 0:
                    # If there are failures but no URLs, assume 100% failure rate and 0% success rate
                    scraper_rates[scraper] = {"success": 0.0, "failure": 100.0}
            
            return scraper_rates
