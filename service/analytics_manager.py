from typing import List

from helper.logger import setup_logger
from helper.singleton import singleton
from model.analytics_models import AnalyticsModel, AnalyticsModelItem
from model.sql_models import ScraperOutput, ScraperFailure, UploadedResource, ScraperAnalytics
from repository.scraper_analytics_repository import ScraperAnalyticsRepository
from repository.scraper_failure_repository import ScraperFailureRepository
from repository.scraper_output_repository import ScraperOutputRepository
from repository.uploaded_resource_repository import UploadedResourceRepository


@singleton
class AnalyticsManager:
    def __init__(self):
        self._logger = setup_logger(self.__class__.__name__)

        self._scraper_failure_repository = ScraperFailureRepository()
        self._scraper_output_repository = ScraperOutputRepository()
        self._uploaded_resource_repository = UploadedResourceRepository()

        self._scraper_analytics_repository = ScraperAnalyticsRepository()

    def _get_scraped_analytics(self, scraper: str) -> AnalyticsModelItem:
        """
        Get the scraped analytics. This includes the succeeded as well as failed resources collected during scraping.

        Args:
            scraper (str): The scraper to analyze.

        Returns:
            AnalyticsModel: The analytics model
        """
        from helper.utils import extract_lists, build_analytics

        scrape_success: ScraperOutput | None = self._scraper_output_repository.get_one_by({"scraper": scraper})
        if not scrape_success:
            raise ValueError(f"Scraper {scraper} not found in the database.")

        scrape_failures: List[ScraperFailure] = self._scraper_failure_repository.get_by({"scraper": scraper})

        return build_analytics(extract_lists(scrape_success.output_json), [failure.source for failure in scrape_failures])

    def _get_content_retrieved_analytics(self, scraper: str) -> AnalyticsModelItem:
        """
        Get the content retrieved analytics. This includes those resources successfully collected during the scraping
        but which contents were not finally retrieved from the remote URLs.

        Args:
            scraper (str): The scraper to analyze.

        Returns:
            AnalyticsModel: The analytics model
        """
        from helper.utils import extract_lists, build_analytics

        scrape_success: ScraperOutput | None = self._scraper_output_repository.get_one_by({"scraper": scraper})
        if not scrape_success:
            raise ValueError(f"Scraper {scraper} not found in the database.")

        scrape_success_as_list = extract_lists(scrape_success.output_json)

        contents_retrieved: List[UploadedResource] = self._uploaded_resource_repository.get_by({"scraper": scraper})

        successes = []
        failures = []
        for resource in scrape_success_as_list:
            for content_retrieved in contents_retrieved:
                if resource == content_retrieved.source or content_retrieved.success:
                    successes.append(resource)
                else:
                    failures.append(resource)

        return build_analytics(successes, failures)

    def _get_uploaded_analytics(self, scraper: str) -> AnalyticsModelItem:
        """
        Get the uploaded analytics. This includes those resources successfully collected during the scraping
        and which contents were finally retrieved from the remote URLs.

        Args:
            scraper (str): The scraper to analyze.

        Returns:
            AnalyticsModel: The analytics model
        """
        from helper.utils import build_analytics

        successes: List[UploadedResource] = self._uploaded_resource_repository.get_by({"scraper": scraper, "success": True})
        failures: List[UploadedResource] = self._uploaded_resource_repository.get_by({"scraper": scraper, "success": False})

        return build_analytics(
            [success.source for success in successes],
            [failure.source for failure in failures],
        )

    def build_and_store_analytics(self, scraper: str) -> int:
        """
        Store the analytics in the database.

        Args:
            scraper (str): The scraper to analyze.

        Returns:
            int: the ID of the inserted record
        """
        try:
            analytics = AnalyticsModel(
                scraped=self._get_scraped_analytics(scraper),
                content_retrieved=self._get_content_retrieved_analytics(scraper),
                uploaded=self._get_uploaded_analytics(scraper),
            )

            return self._scraper_analytics_repository.save_analytics(scraper, analytics)
        except ValueError as e:
            self._logger.error(f"Failed to get analytics for scraper {scraper}. Error: {e}")

    def find_latest_analytics(self, scraper: str) -> AnalyticsModel | None:
        """
        Find the past analytics for a scraper, if any, in the database.

        Args:
            scraper (str): The scraper to analyze.

        Returns:
            AnalyticsModel: The analytics model if found, None otherwise.
        """
        analytics_db: List[ScraperAnalytics] = self._scraper_analytics_repository.get_by(
            {"scraper": scraper},
            order_by="created_at",
            desc=True,
            limit=1,
        )

        if not analytics_db:
            self._logger.warning(f"No analytics found for scraper {scraper}.")
            return None

        return AnalyticsModel(**analytics_db[0].result_json)
