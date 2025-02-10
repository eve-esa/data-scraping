from typing import Type

from model.sql_models import ScraperFailure
from repository.base_repository import BaseRepository


class ScraperFailureRepository(BaseRepository):
    @property
    def model_type(self) -> Type[ScraperFailure]:
        return ScraperFailure
