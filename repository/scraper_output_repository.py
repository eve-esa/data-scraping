from typing import Type

from model.sql_models import ScraperOutput
from repository.base_repository import BaseRepository


class ScraperOutputRepository(BaseRepository):
    @property
    def model_type(self) -> Type[ScraperOutput]:
        return ScraperOutput
