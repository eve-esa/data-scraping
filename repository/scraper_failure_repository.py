from typing import List, Type

from model.sql_models import ScraperFailure
from repository.base_repository import BaseRepository


class ScraperFailureRepository(BaseRepository):
    def delete_by_scraper(self, scraper: str) -> bool:
        """
        Delete a failure from the database by its scraper

        Args:
            scraper (str): The scraper of the failure

        Returns:
            bool: True if the failure was deleted, False otherwise
        """
        return self.delete_by({"scraper": scraper})

    @property
    def table_name(self) -> str:
        return "scraper_failures"

    @property
    def model_type(self) -> Type[ScraperFailure]:
        return ScraperFailure

    @property
    def model_fields_excluded(self) -> List[str]:
        return ["id"]
