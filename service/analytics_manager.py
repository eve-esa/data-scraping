from typing import Dict
from helper.singleton import singleton
from sqlalchemy import text
import json

from service.database_manager import DatabaseManager

@singleton
class AnalyticsManager:
    def __init__(self):
        self.db = DatabaseManager()
        
    def get_success_failure_rates(self, scraper_name: str = None) -> Dict[str, Dict[str, float]]:
        """Calculate scraper success and failure rates for all scrapers or a specific one
        
        Args:
            scraper_name (str, optional): Specific scraper to analyze. Defaults to None (all scrapers).
        
        Returns:
            Dict[str, Dict[str, float]]: A dictionary of scraper names and their sucesss and failure rate.
        """
        with self.db.engine.connect() as connection:
            # Build query conditions based on scraper_name
            scraper_condition = ""
            if scraper_name:
                scraper_condition = " WHERE scraper = :scraper_name"
            
            # Get outputs and failures
            outputs = connection.execute(
                text(f"SELECT scraper, output FROM scraper_outputs{scraper_condition}"),
                {"scraper_name": scraper_name} if scraper_name else {}
            ).fetchall()
            
            failures = connection.execute(
                text(f"SELECT * FROM scraper_failures{scraper_condition}"),
                {"scraper_name": scraper_name} if scraper_name else {}
            ).fetchall()
            
            # Process scraper outputs to count total items per scraper
            scraper_totals = {}
            for output in outputs:
                scraper = output[0]
                try:
                    data = json.loads(output[1])
                    # Count all items recursively in the output
                    total_items = self._count_items_recursive(data)
                    scraper_totals[scraper] = scraper_totals.get(scraper, 0) + total_items
                except json.JSONDecodeError:
                    continue
            
            # Count failures per scraper
            failure_counts = {}
            for failure in failures:
                scraper = failure[1]
                if scraper:
                    failure_counts[scraper] = failure_counts.get(scraper, 0) + 1
            
            return self._calculate_rates(scraper_totals, failure_counts)
    
    def _count_items_recursive(self, data) -> int:
        """Recursively count items in nested data structures
        Args:
            data: The data to process. Can be a list, dictionary, or other types.
        
        Returns:
            int: The total count of items in the data structure.
        """
        if isinstance(data, list):
            return sum(self._count_items_recursive(item) for item in data)
        elif isinstance(data, dict):
            return sum(self._count_items_recursive(value) for value in data.values())
        else:
            return 1
    
    def _calculate_rates(self, totals: Dict[str, int], failures: Dict[str, int]) -> Dict[str, Dict[str, float]]:
        """Calculate success and failure rates from totals and failures
        Args:
            totals (Dict[str, int]): A dictionary where the key is the scraper name, and the value is the total count of items.
            failures (Dict[str, int]): A dictionary where the key is the scraper name, and the value is the count of failures.
        
        Returns:
            Dict[str, Dict[str, float]]: A dictionary where the key is the scraper name, and the value is another dictionary
            with the success and failure rates for that scraper. The rates are rounded to two decimal places.
        """
        rates = {}
        for scraper in set(totals.keys()) | set(failures.keys()):
            total = totals.get(scraper, 0)
            failure_count = failures.get(scraper, 0)
            
            if total > 0:
                failure_percentage = (failure_count / total) * 100
                success_percentage = 100.0 - failure_percentage
                rates[scraper] = {
                    "success": round(success_percentage, 2),
                    "failure": round(failure_percentage, 2)
                }
            elif failure_count > 0:
                rates[scraper] = {"success": 0.0, "failure": 100.0}
        
        return rates
    
    def get_all_analytics(self, scraper_name: str = None) -> Dict[str, Dict]:
        """Collect all analytics in one dictionary
        
        Args:
            scraper_name (str, optional): Specific scraper to analyze. Defaults to None (all scrapers).
        
        Returns:
            Dict[str, Dict]: A dictionary containing all analytics.
        """
        return {
            "success_failure_rates": self.get_success_failure_rates(scraper_name)
        }
