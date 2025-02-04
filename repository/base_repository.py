from abc import ABC, abstractmethod
from typing import List, Dict, Any, Type

from helper.logger import setup_logger
from model.sql_models import BaseModel, DatabaseFieldType
from service.database_manager import DatabaseManager


class BaseRepository(ABC):
    def __init__(self):
        self._logger = setup_logger(self.__class__.__name__)
        self._database_manager = DatabaseManager()

    def before_insert(self, record: Dict, keys_to_purge: List | None = None) -> Dict:
        if not keys_to_purge:
            keys_to_purge = ["id"]
        elif "id" not in keys_to_purge:
            keys_to_purge.append("id")

        for key in keys_to_purge:
            del record[key]

        return record

    def insert(self, record: BaseModel, keys_to_purge: List | None = None) -> int:
        """
        Store the record in the database

        Args:
            record (BaseModel): The record to store
            keys_to_purge (List[str]): The keys to purge from the record before inserting it into the database

        Returns:
            ID of the appended record
        """
        record_dict = self.before_insert(record.model_dump(), keys_to_purge)
        return self._database_manager.insert_record(self.table_name, record_dict)

    def upsert(
        self,
        record: BaseModel,
        search_by: Dict[str, Any],
        update_dict: Dict[str, Any],
        keys_to_purge: List | None = None
    ) -> int:
        """
        Store the output in the database

        Args:
            record (BaseModel): The output to store
            search_by (Dict[str, Any]): The search criteria to check if the record already exists
            update_dict (Dict[str, Any]): The fields to update if the record already
            keys_to_purge (List[str]): The keys to purge from the record before inserting it into the database

        Returns:
            ID of the appended record
        """
        record_dict = self.before_insert(record.model_dump(), keys_to_purge)

        existing_records = self._database_manager.search_records(self.table_name, search_by, limit=1)
        if existing_records:
            existing_record = existing_records[0]
            self._database_manager.update_record(self.table_name, existing_record["id"], update_dict)
            return existing_record["id"]

        return self._database_manager.insert_record(self.table_name, record_dict)

    @property
    def model_fields(self) -> List:
        return [field for field in self.model_type.model_fields.keys() if field not in ["id", "content"]]

    @property
    def model_fields_definition(self) -> Dict[str, DatabaseFieldType]:
        return self.model_type.def_types()

    @property
    @abstractmethod
    def table_name(self) -> str:
        pass

    @property
    @abstractmethod
    def model_type(self) -> Type[BaseModel]:
        pass

    @property
    @abstractmethod
    def model_fields_excluded(self) -> List[str]:
        pass
