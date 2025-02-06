from typing import List, Type

from model.sql_models import ScraperOutput
from repository.base_repository import BaseRepository


class ScraperOutputRepository(BaseRepository):
    def get_by_scraper(self, scraper: str) -> ScraperOutput | None:
        """
        Retrieve an output from the database by its scraper

        Args:
            scraper (str): The scraper of the output

        Returns:
            ScraperOutput | None: The output if found, or None otherwise
        """
        return self.get_one_by({"scraper": scraper})

    @property
    def table_name(self) -> str:
        return "scraper_outputs"

    @property
    def model_type(self) -> Type[ScraperOutput]:
        return ScraperOutput

    @property
    def model_fields_excluded(self) -> List[str]:
        return ["id"]
