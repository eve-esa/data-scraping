import json
from typing import Type

from model.analytics_models import AnalyticsModel
from model.sql_models import ScraperAnalytics
from repository.base_repository import BaseRepository


class ScraperAnalyticsRepository(BaseRepository):
    def save_analytics(self, scraper: str, analytics: AnalyticsModel):
        return self.insert(
            ScraperAnalytics(scraper=scraper, result=json.dumps(analytics.model_dump()))
        )

    @property
    def model_type(self) -> Type[ScraperAnalytics]:
        return ScraperAnalytics
