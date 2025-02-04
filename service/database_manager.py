import os
from typing import List, Dict, Any, Optional
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, inspect
from sqlalchemy.orm import sessionmaker, declarative_base

from helper.singleton import singleton
from helper.database import type_mapping
from model.sql_models import DatabaseFieldType


Base = declarative_base()


@singleton
class DatabaseManager:
    def __init__(self):
        """
        Initialize the database manager
        """
        self.db_user = os.getenv("DB_USER", "root")
        self.db_password = os.getenv("DB_PASSWORD", "")
        self.db_host = os.getenv("DB_HOST", "localhost")
        self.db_port = os.getenv("DB_PORT", "3306")
        self.db_name = os.getenv("DB_NAME", "mydatabase")

        db_url = f"mysql+pymysql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"

        self.engine = create_engine(db_url)
        self.metadata = MetaData()

    def create_table(self, table_name: str, columns: Dict[str, DatabaseFieldType]) -> None:
        """
        Create a new table in the database

        Args:
            table_name: Name of the table
            columns: Dictionary with the column names and types
        """
        table_columns = [
            Column('id', Integer, primary_key=True, autoincrement=True)
        ]

        for col_name, col_type in columns.items():
            sql_type = type_mapping().get(col_type, String(length=255))
            table_columns.append(Column(col_name, sql_type))

        Table(table_name, self.metadata, *table_columns)
        self.metadata.create_all(self.engine)

    def get_table_info(self, table_name: str) -> List[Dict[str, str]]:
        """
        Retrieve detailed information about the table structure

        Args:
            table_name: Name of the table

        Returns:
            List of dictionaries, each containing information about a column
        """
        inspector = inspect(self.engine)
        columns = inspector.get_columns(table_name)

        return [
            {
                "name": col["name"],
                "type": str(col["type"]),
                "notnull": not col["nullable"],
                "default_value": col["default"],
                "pk": col["primary_key"]
            }
            for col in columns
        ]

    def get_column_names(self, table_name: str) -> List[str]:
        """
        Retrieve only the names of the columns of the table

        Args:
            table_name: Name of the table

        Returns:
            List of column names
        """
        return [col["name"] for col in self.get_table_info(table_name)]

    def get_record(self, table_name: str, record_id: int) -> Dict[str, Any] | None:
        """
        Retrieve a record from the database

        Args:
            table_name: Name of the table
            record_id: ID of the record

        Returns:
            Dictionary with the record data, or None if the record was not found
        """
        session = sessionmaker(bind=self.engine, expire_on_commit=True)()

        table = Table(table_name, self.metadata, autoload_with=self.engine)
        result = session.query(table).filter_by(id=record_id).first()

        session.close()

        if result:
            return dict(result._mapping)
        return None

    def insert_record(self, table_name: str, data: Dict[str, Any]) -> int:
        """
        Insert a new record into the database

        Args:
            table_name: Name of the table
            data: Dictionary with the record data

        Returns:
            ID of the inserted record
        """
        session = sessionmaker(bind=self.engine, expire_on_commit=True)()

        table = Table(table_name, self.metadata, autoload_with=self.engine)
        result = session.execute(table.insert().values(**data))
        session.commit()
        session.close()

        return result.inserted_primary_key[0]

    def update_record(self, table_name: str, record_id: int, data: Dict[str, Any]) -> bool:
        """
        Update an existing record

        Args:
            table_name: Name of the table
            record_id: ID of the record
            data: Dictionary with the updated data

        Returns:
            True if the update was successful
        """
        session = sessionmaker(bind=self.engine, expire_on_commit=True)()

        table = Table(table_name, self.metadata, autoload_with=self.engine)
        result = session.execute(
            table.update()
            .where(table.c.id == record_id)
            .values(**data)
        )
        session.commit()
        session.close()
        return result.rowcount > 0

    def delete_record(self, table_name: str, record_id: int) -> bool:
        """
        Delete a record from the database

        Args:
            table_name: Name of the table
            record_id: ID of the record

        Returns:
            True if the deletion was successful
        """
        session = sessionmaker(bind=self.engine, expire_on_commit=True)()

        table = Table(table_name, self.metadata, autoload_with=self.engine)
        result = session.execute(
            table.delete().where(table.c.id == record_id)
        )
        session.commit()
        session.close()

        return result.rowcount > 0

    def delete_record_by(self, table_name: str, conditions: Dict[str, Any], operator: str = "AND") -> bool:
        """
        Delete a record from the database, based on certain conditions

        Args:
            table_name: Name of the table
            conditions: Dictionary with the search criteria
            operator: Logical operator between conditions ("AND" or "OR")

        Returns:
            True if the deletion was successful
        """
        session = sessionmaker(bind=self.engine, expire_on_commit=True)()

        table = Table(table_name, self.metadata, autoload_with=self.engine)
        query = session.query(table)

        # Build filter conditions
        if operator.upper() == "AND":
            query = query.filter_by(**conditions)
        else:  # OR
            from sqlalchemy import or_
            or_conditions = [getattr(table.c, k) == v for k, v in conditions.items()]
            query = query.filter(or_(*or_conditions))

        result = query.delete()
        session.commit()
        session.close()

        return result > 0

    def get_all_records(self, table_name: str) -> List[Dict[str, Any]]:
        """
        Retrieve all records from the database

        Args:
            table_name: Name of the table

        Returns:
            List of dictionaries, each representing a record
        """
        session = sessionmaker(bind=self.engine, expire_on_commit=True)()

        table = Table(table_name, self.metadata, autoload_with=self.engine)
        result = session.query(table).all()
        session.close()

        return [dict(row._mapping) for row in result]

    def search_records(
        self,
        table_name: str,
        conditions: Dict[str, Any],
        operator: str = "AND",
        order_by: Optional[str] = None,
        desc: bool = False,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Search records that match certain conditions

        Args:
            table_name: Name of the table
            conditions: Dictionary with the search criteria
            operator: Logical operator between conditions ("AND" or "OR")
            order_by: Column to order by
            desc: Whether to sort in descending order
            limit: Maximum number of records to retrieve

        Returns:
            List of dictionaries, each representing a record
        """
        session = sessionmaker(bind=self.engine, expire_on_commit=True)()

        table = Table(table_name, self.metadata, autoload_with=self.engine)
        query = session.query(table)

        # Build filter conditions
        if operator.upper() == "AND":
            query = query.filter_by(**conditions)
        else:  # OR
            from sqlalchemy import or_
            or_conditions = [getattr(table.c, k) == v for k, v in conditions.items()]
            query = query.filter(or_(*or_conditions))

        # Apply ordering
        if order_by:
            column = getattr(table.c, order_by)
            query = query.order_by(column.desc() if desc else column.asc())

        # Apply limit
        if limit:
            query = query.limit(limit)

        result = query.all()
        session.close()

        return [dict(row._mapping) for row in result]
