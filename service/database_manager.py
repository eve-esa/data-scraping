from contextlib import contextmanager
import os
import time
from typing import List, Dict, Any
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, inspect
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import or_

from helper.singleton import singleton
from model.sql_models import DatabaseFieldDefinition


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

        self.engine = create_engine(
            db_url,
            pool_recycle=3600,
            pool_timeout=30,
            pool_pre_ping=True,
            connect_args={
                "connect_timeout": 10,
                "read_timeout": 30,
                "write_timeout": 30,
            }
        )

    def execute_with_retry(self, operation: callable, max_retries: int | None = 3, retry_delay: float | None = 1):
        """
        Execute a database operation with retry logic

        Args:
            operation: Function that performs the database operation
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retries in seconds

        Returns:
            Result of the operation
        """
        retries = 0
        last_error = None

        while retries < max_retries:
            try:
                return operation()
            except OperationalError as e:
                if "2013" in str(e) or "Lost connection" in str(e):
                    retries += 1
                    last_error = e
                    time.sleep(retry_delay * retries)
                    continue
                raise
            except SQLAlchemyError as e:
                raise

        raise last_error

    @contextmanager
    def session_scope(self):
        """
        Provide a transactional scope around a series of operations.
        """
        session = sessionmaker(bind=self.engine, expire_on_commit=True)()
        try:
            yield session
            session.commit()
        except:
            session.rollback()
            raise
        finally:
            session.close()

    def create_table(self, table_name: str, columns: Dict[str, DatabaseFieldDefinition]) -> None:
        """
        Create a new table in the database

        Args:
            table_name: Name of the table
            columns: Dictionary with the column definitions
        """
        table_columns = [
            Column('id', Integer, primary_key=True, autoincrement=True)
        ]

        for col_name, col_def in columns.items():
            table_columns.append(
                Column(name=col_name, type_=col_def.type, default=col_def.default, nullable=col_def.nullable)
            )

        metadata = MetaData()
        Table(table_name, metadata, *table_columns)
        metadata.create_all(self.engine)

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

    def get_table(self, table_name: str):
        return Table(table_name, MetaData(), autoload_with=self.engine)

    def get_record(self, table_name: str, record_id: int) -> Dict[str, Any] | None:
        """
        Retrieve a record from the database

        Args:
            table_name: Name of the table
            record_id: ID of the record

        Returns:
            Dictionary with the record data, or None if the record was not found
        """
        def operation():
            with self.session_scope() as session:
                result = session.query(self.get_table(table_name)).filter_by(id=record_id).first()
                return dict(result._mapping) if result else None

        return self.execute_with_retry(operation)

    def insert_record(self, table_name: str, data: Dict[str, Any]) -> int:
        """
        Insert a new record into the database

        Args:
            table_name: Name of the table
            data: Dictionary with the record data

        Returns:
            ID of the inserted record
        """
        def operation():
            with self.session_scope() as session:
                result = session.execute(self.get_table(table_name).insert().values(**data))
                return result.inserted_primary_key[0]

        return self.execute_with_retry(operation)

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
        def operation():
            with self.session_scope() as session:
                table = self.get_table(table_name)
                result = session.execute(
                    table.update()
                    .where(table.c.id == record_id)
                    .values(**data)
                )
                return result.rowcount > 0

        return self.execute_with_retry(operation)

    def delete_record(self, table_name: str, record_id: int) -> bool:
        """
        Delete a record from the database

        Args:
            table_name: Name of the table
            record_id: ID of the record

        Returns:
            True if the deletion was successful
        """
        def operation():
            with self.session_scope() as session:
                table = self.get_table(table_name)
                result = session.execute(
                    table.delete().where(table.c.id == record_id)
                )
                return result.rowcount > 0

        return self.execute_with_retry(operation)

    def delete_records_by(self, table_name: str, conditions: Dict[str, Any], operator: str = "AND") -> bool:
        """
        Delete records from the database, based on certain conditions

        Args:
            table_name: Name of the table
            conditions: Dictionary with the search criteria
            operator: Logical operator between conditions ("AND" or "OR")

        Returns:
            True if the deletion was successful
        """
        def operation():
            with self.session_scope() as session:
                table = self.get_table(table_name)
                query = session.query(table)
                # Build filter conditions
                if operator.upper() == "AND":
                    query = query.filter_by(**conditions)
                else:  # OR
                    or_conditions = [getattr(table.c, k) == v for k, v in conditions.items()]
                    query = query.filter(or_(*or_conditions))
                result = query.delete()
                return result > 0

        return self.execute_with_retry(operation)

    def delete_all_records(self, table_name: str) -> bool:
        """
        Delete all records from the database

        Args:
            table_name: Name of the table

        Returns:
            True if the deletion was successful
        """
        def operation():
            with self.session_scope() as session:
                result = session.query(self.get_table(table_name)).delete()
                return result > 0

        return self.execute_with_retry(operation)

    def get_all_records(self, table_name: str) -> List[Dict[str, Any]]:
        """
        Retrieve all records from the database

        Args:
            table_name: Name of the table

        Returns:
            List of dictionaries, each representing a record
        """
        def operation():
            with self.session_scope() as session:
                result = session.query(self.get_table(table_name)).all()
                return [dict(row._mapping) for row in result]

        return self.execute_with_retry(operation)

    def search_records(
        self,
        table_name: str,
        conditions: Dict[str, Any],
        operator: str = "AND",
        order_by: str | None = None,
        group_by: str | None = None,
        desc: bool = False,
        limit: int | None = None
    ) -> List[Dict[str, Any]]:
        """
        Search records that match certain conditions

        Args:
            table_name: Name of the table
            conditions: Dictionary with the search criteria
            operator: Logical operator between conditions ("AND" or "OR")
            order_by: Column to order by
            group_by: Column to group by
            desc: Whether to sort in descending order
            limit: Maximum number of records to retrieve

        Returns:
            List of dictionaries, each representing a record
        """
        def operation():
            with self.session_scope() as session:
                table = self.get_table(table_name)
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
                if group_by:
                    column = getattr(table.c, group_by)
                    query = query.group_by(column)
                # Apply limit
                if limit:
                    query = query.limit(limit)
                result = query.all()
                return [dict(row._mapping) for row in result]

        return self.execute_with_retry(operation)