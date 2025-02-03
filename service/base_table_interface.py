from abc import ABC, abstractmethod
from typing import List, Dict

from helper.logger import setup_logger
from service.database_manager import DatabaseManager


class BaseTableInterface(ABC):
    def __init__(self):
        self._logger = setup_logger(self.__class__.__name__)
        self._database_manager = DatabaseManager()

    @property
    @abstractmethod
    def table_name(self) -> str:
        pass

    @property
    @abstractmethod
    def model_fields(self) -> List:
        pass

    @property
    @abstractmethod
    def model_fields_definition(self) -> Dict:
        pass
