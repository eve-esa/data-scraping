from typing import List, Type

from model.sql_models import ScraperFailure
from repository.base_repository import BaseRepository


class ScraperFailureRepository(BaseRepository):
    @property
    def table_name(self) -> str:
        return "scraper_failures"

    @property
    def model_type(self) -> Type[ScraperFailure]:
        return ScraperFailure

    @property
    def model_fields_excluded(self) -> List[str]:
        return ["id"]
