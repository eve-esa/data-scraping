from datetime import datetime
from typing import List, Dict
from pydantic import BaseModel, Field

from service.base_table_interface import BaseTableInterface


class Output(BaseModel):
    id: int | None = None
    publisher: str
    output: str
    date: datetime | None = Field(default_factory=lambda: datetime.now())


class OutputManager(BaseTableInterface):
    def get_by_publisher(self, publisher: str) -> Output | None:
        """
        Retrieve an output from the database by its publisher

        Args:
            publisher (str): The publisher of the output

        Returns:
            Output | None: The output if found, or None otherwise
        """
        record = self._database_manager.search_records(self.table_name, {"publisher": publisher})
        if record:
            return Output(**record)
        return None

    def upsert(self, output: Output) -> int:
        """
        Store the resource in the database

        Args:
            output (Output): The output to store

        Returns:
            ID of the appended record
        """
        output_dict = output.model_dump()
        if "id" in output_dict:
            del output_dict["id"]
        if "date" in output_dict:
            del output_dict["date"]

        # check whether a record with the same publisher already exists: if so, update it with the output, otherwise insert a new record
        existing_records = self._database_manager.search_records(self.table_name, {"publisher": output.publisher}, limit = 1)
        if existing_records:
            existing_record = existing_records[0]
            self._database_manager.update_record(self.table_name, existing_record["id"], {"output": output.output})
            return existing_record["id"]

        return self._database_manager.insert_record(self.table_name, output_dict)

    @property
    def table_name(self) -> str:
        return "outputs"

    @property
    def model_fields(self) -> List:
        return [field for field in Output.model_fields.keys() if field != "id"]

    @property
    def model_fields_definition(self) -> Dict:
        return {field: "TEXT" for field in self.model_fields}
