from typing import List, Dict

from model.sql_models import Output
from service.base_table_interface import BaseTableInterface
from service.database_manager import DatabaseFieldType


class OutputManager(BaseTableInterface):
    def get_by_scraper(self, scraper: str) -> Output | None:
        """
        Retrieve an output from the database by its scraper

        Args:
            scraper (str): The scraper of the output

        Returns:
            Output | None: The output if found, or None otherwise
        """
        record = self._database_manager.search_records(self.table_name, {"scraper": scraper}, limit=1)
        if record:
            return Output(**record[0])
        return None

    @property
    def table_name(self) -> str:
        return "outputs"

    @property
    def model_fields(self) -> List:
        return [field for field in Output.model_fields.keys() if field not in ["id", "_output_json"]]

    @property
    def model_fields_definition(self) -> Dict:
        return {field: DatabaseFieldType.TEXT for field in self.model_fields}
