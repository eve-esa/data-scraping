from typing import List, Type

from model.sql_models import ScraperOutput
from repository.base_repository import BaseRepository


class ScraperOutputRepository(BaseRepository):
    @property
    def table_name(self) -> str:
        return "scraper_outputs"

    @property
    def model_type(self) -> Type[ScraperOutput]:
        return ScraperOutput

    @property
    def model_fields_excluded(self) -> List[str]:
        return ["id"]
