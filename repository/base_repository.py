from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Dict, Any, Type

from helper.logger import setup_logger
from model.sql_models import BaseModel, DatabaseFieldDefinition, DatabaseRelationDefinition
from service.database_manager import DatabaseManager


class BaseRepository(ABC):
    def __init__(self):
        self._logger = setup_logger(self.__class__.__name__)
        self._database_manager = DatabaseManager()

    def before_insert(self, record: BaseModel, keys_to_purge: List | None = None) -> Dict:
        record_dict = record.model_dump()
        record_dict = {
            (k if not isinstance(v, dict) else f"{k}_id"): v if not isinstance(v, dict) else v["id"]
            for k, v in record_dict.items()
        }

        if not keys_to_purge:
            keys_to_purge = ["id"]
        elif "id" not in keys_to_purge:
            keys_to_purge.append("id")

        for key in keys_to_purge:
            del record_dict[key]

        return record_dict

    def insert(self, record: BaseModel, keys_to_purge: List | None = None) -> int:
        """
        Store the record in the database

        Args:
            record (BaseModel): The record to store
            keys_to_purge (List[str]): The keys to purge from the record before inserting it into the database

        Returns:
            ID of the appended record
        """
        record_dict = self.before_insert(record, keys_to_purge)
        return self._database_manager.insert_record(self.table_name, record_dict)

    def upsert(
        self,
        record: BaseModel,
        search_by: Dict[str, Any],
        update_dict: Dict[str, Any] | None = None,
        order_by: str | None = None,
        group_by: str | None = None,
        desc: bool = False,
        keys_to_purge: List | None = None
    ) -> int:
        """
        Store the output in the database

        Args:
            record (BaseModel): The output to store
            search_by (Dict[str, Any]): The search criteria to check if the record already exists
            update_dict (Dict[str, Any]): The fields to update if the record already. If None, the entire record will be dumped, except the eventually purged keys
            order_by (str): The field to order by
            group_by (str): The field to group by
            desc (bool): Whether to sort in descending order
            keys_to_purge (List[str]): The keys to purge from the record before inserting it into the database

        Returns:
            ID of the appended record
        """
        record_dict = self.before_insert(record, keys_to_purge)
        update_dict = update_dict or record_dict

        existing_records = self._database_manager.search_records(
            self.table_name, search_by, order_by=order_by, group_by=group_by, desc=desc
        )
        if existing_records:
            existing_record = existing_records[0]
            update_dict["last_access_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            self._database_manager.update_record(self.table_name, existing_record["id"], update_dict)
            return existing_record["id"]

        return self._database_manager.insert_record(self.table_name, record_dict)

    def get(self, record_id: int) -> BaseModel:
        """
        Get the record from the database

        Args:
            record_id (int): The ID of the record

        Returns:
            BaseModel: The record
        """
        record = self._database_manager.get_record(self.table_name, record_id)
        return self.model_type(**record)

    def get_all(self) -> List[BaseModel]:
        """
        Get all records from the database

        Returns:
            List[BaseModel]: The records
        """
        records = self._database_manager.get_all_records(self.table_name)
        return [self.model_type(**record) for record in records]

    def get_by(
        self,
        conditions: Dict[str, Any],
        operator: str = "AND",
        order_by: str | None = None,
        group_by: str | None = None,
        desc: bool = False,
        limit: int | None = None
    ) -> List[BaseModel]:
        """
        Get records from the database by their condition criteria and order them by a field if specified with the option
        to sort them in descending order and limit the number of records to retrieve from the database if specified

        Args:
            conditions (Dict[str, Any]): The condition criteria
            operator (str): The operator to use for the condition
            order_by (str): The field to order by
            group_by (str): The field to group by
            desc (bool): Whether to sort in descending order
            limit (int): Maximum number of records to retrieve

        Returns:
            List[BaseModel]: The records that match the condition criteria and ordered by the specified field
        """
        records = self._database_manager.search_records(
            self.table_name, conditions, operator, order_by, group_by, desc, limit
        )
        return [self.model_type(**record) for record in records]

    def get_one_by(
        self,
        conditions: Dict[str, Any],
        operator: str = "AND",
        order_by: str | None = None,
        group_by: str | None = None,
        desc: bool = False,
    ) -> BaseModel | None:
        """
        Get the first record from the database by its condition criteria and order them by a field if specified with the
        option to sort them in descending order

        Args:
            conditions (Dict[str, Any]): The condition criteria
            operator (str): The operator to use for the condition
            order_by (str): The field to order by
            group_by (str): The field to group by
            desc (bool): Whether to sort in descending order

        Returns:
            BaseModel | None: The first record that matches the condition criteria and ordered by the specified field or None
        """
        records = self._database_manager.search_records(
            self.table_name, conditions, operator, order_by, group_by, desc, limit=1
        )
        if not records:
            return None
        return self.model_type(**records[0])

    def delete(self, record_id: int) -> bool:
        """
        Delete a record from the database by its ID

        Args:
            record_id (int): The ID of the record

        Returns:
            bool: True if the deletion was successful
        """
        return self._database_manager.delete_record(self.table_name, record_id)

    def delete_all(self) -> bool:
        """
        Delete all records from the database

        Returns:
            bool: True if the deletion was successful
        """
        return self._database_manager.delete_all_records(self.table_name)

    def delete_by(self, condition: Dict[str, Any], operator: str = "AND") -> bool:
        """
        Delete a record from the database by its condition criteria

        Args:
            condition (Dict[str, Any]): The condition criteria
            operator (str): The operator to use for the condition

        Returns:
            bool: True if the deletion was successful
        """
        return self._database_manager.delete_records_by(self.table_name, condition, operator)

    @property
    def model_fields(self) -> List:
        return [field for field in self.model_type.model_fields.keys() if field not in ["id", "content"]]

    @property
    def model_fields_definition(self) -> Dict[str, DatabaseFieldDefinition]:
        return self.model_type.def_types()

    @property
    def model_relations_definition(self) -> List[DatabaseRelationDefinition]:
        return self.model_type.def_relations()

    @property
    def table_name(self) -> str:
        return self.model_type.table_name()

    @property
    @abstractmethod
    def model_type(self) -> Type[BaseModel]:
        pass
