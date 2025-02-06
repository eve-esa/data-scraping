from typing import Dict, Any
from sqlalchemy import Integer, String, Text, Numeric, Boolean
import importlib
import inspect
import pkgutil

from model.sql_models import DatabaseFieldType


def init_db():
    """
    Initialize the database.
    """
    from repository.base_repository import BaseRepository
    from service.database_manager import DatabaseManager

    base_package = "repository"
    package = importlib.import_module(base_package)

    discovered_db_table_managers = {}
    for _, module_name, _ in pkgutil.iter_modules(package.__path__):
        module = importlib.import_module(f"{base_package}.{module_name}")

        discovered_db_table_managers |= {
            name: obj_type
            for name, obj_type in inspect.getmembers(module)
            if inspect.isclass(obj_type)
               and issubclass(obj_type, BaseRepository)
               and not inspect.isabstract(obj_type)
        }

    database_manager = DatabaseManager()

    for db_table_manager_class in discovered_db_table_managers.values():
        db_table_manager = db_table_manager_class()
        table = db_table_manager.table_name
        database_manager.create_table(table, db_table_manager.model_fields_definition)


def type_mapping() -> Dict[DatabaseFieldType, Any]:
    return {
        DatabaseFieldType.TEXT: Text,
        DatabaseFieldType.INTEGER: Integer,
        DatabaseFieldType.VARCHAR: String(length=255),
        DatabaseFieldType.FLOAT: Numeric,
        DatabaseFieldType.BOOLEAN: Boolean,
    }
