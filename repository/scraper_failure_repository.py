from typing import Type, List
from sqlalchemy import func

from model.sql_models import ScraperFailure
from repository.base_repository import BaseRepository


class ScraperFailureRepository(BaseRepository):
    def get_by_scraper_and_latest_source(self, scraper: str) -> List[ScraperFailure]:
        session = self._database_manager.get_session()
        table = self._database_manager.get_table(self.table_name)

        subquery = session.query(
            table.c.source,
            func.max(table.c.last_access_at).label("max_last_access")
        ).filter(
            table.c.scraper == scraper
        ).group_by(
            table.c.source
        ).subquery()

        query = session.query(table).join(
            subquery,
            (table.c.source == subquery.c.source) &
            (table.c.last_access_at == subquery.c.max_last_access)
        ).filter(
            table.c.scraper == scraper
        )

        records = [dict(row._mapping) for row in query.all()]
        session.close()

        return [self.model_type(**record) for record in records]

    @property
    def model_type(self) -> Type[ScraperFailure]:
        return ScraperFailure
