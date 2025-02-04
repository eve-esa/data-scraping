import os
import sqlite3
from typing import List, Dict, Any, Optional

from helper.base_enum import Enum
from helper.singleton import singleton


class DatabaseFieldType(Enum):
    TEXT = "TEXT"
    INTEGER = "INTEGER"
    REAL = "REAL"
    BLOB = "BLOB"


@singleton
class DatabaseManager:
    def __init__(self):
        """
        Initialize the database manager
        """
        self._db_path = os.path.join("database", os.getenv("DB_NAME"))

        self._create_database_if_not_exists()
        self.conn = sqlite3.connect(self._db_path)

    def _create_database_if_not_exists(self) -> None:
        """
        Create the database file if it does not exist. The database is created within the `database` folder
        """
        os.makedirs(os.path.dirname(self._db_path), exist_ok=True)

        if not os.path.exists(self._db_path):
            open(self._db_path, "w").close()

    def create_table(self, table_name: str, columns: Dict[str, DatabaseFieldType]) -> None:
        """
        Create a new table in the database

        Args:
            table_name: Name of the table
            columns: Dictionary with column names and types (e.g., {"name": "TEXT", "age": "INTEGER"})
        """
        cursor = self.conn.cursor()

        columns_def = ", ".join([f"{col} {dtype}" for col, dtype in columns.items()])
        create_table_query = f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            {columns_def}
        )
        """
        cursor.execute(create_table_query)
        self.conn.commit()

    def get_table_info(self, table_name: str) -> List[Dict[str, str]]:
        """
        Retrieve detailed information about the table structure

        Args:
            table_name: Name of the table

        Returns:
            List of dictionaries containing the information of each column:
            - name: name of the column
            - type: tipe of the column
            - notnull: whether the column can contain NULL values (0 or 1)
            - default_value: default value of the column
            - pk: whether the column is part of the primary key (0 or 1)
        """
        cursor = self.conn.cursor()

        query = f"PRAGMA table_info({table_name})"
        cursor.execute(query)
        columns_info = cursor.fetchall()

        return [
            {
                "name": col[1],
                "type": col[2],
                "notnull": col[3],
                "default_value": col[4],
                "pk": col[5]
            }
            for col in columns_info
        ]

    def get_column_names(self, table_name: str) -> List[str]:
        """
        Retrieve only the names of the columns of the table

        Returns:
            List of column names
        """
        return [col["name"] for col in self.get_table_info(table_name)]

    def get_record(self, table_name: str, record_id: int) -> Dict[str, Any] | None:
        """
        Retrieve a record from the database

        Args:
            table_name: Name of the table
            record_id: ID of the record to retrieve

        Returns:
            Dictionary with the record data
        """
        cursor = self.conn.cursor()

        query = f"SELECT * FROM {table_name} WHERE id = ?"
        cursor.execute(query, (record_id,))
        record = cursor.fetchone()

        if record:
            columns = self.get_column_names(table_name)
            return dict(zip(columns, record))
        return None

    def insert_record(self, table_name: str, data: Dict[str, Any]) -> int:
        """
        Insert a new record into the database

        Args:
            table_name: Name of the table
            data: dictionary with the data to insert (e.g., {"name": "Mario", "age": 30})

        Returns:
            ID of the new record
        """
        cursor = self.conn.cursor()

        columns = ", ".join(data.keys())
        placeholders = ", ".join(["?" for _ in data])
        query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"

        cursor.execute(query, list(data.values()))
        self.conn.commit()
        return cursor.lastrowid

    def update_record(self, table_name: str, record_id: int, data: Dict[str, Any]) -> bool:
        """
        Update an existing record

        Args:
            table_name: Name of the table
            record_id: ID of the record to update
            data: Dictionary with the data to update

        Returns:
            True if the update was successful
        """
        cursor = self.conn.cursor()

        set_values = ", ".join([f"{key} = ?" for key in data.keys()])
        query = f"UPDATE {table_name} SET {set_values} WHERE id = ?"

        values = list(data.values()) + [record_id]
        cursor.execute(query, values)
        self.conn.commit()
        return cursor.rowcount > 0

    def delete_record(self, table_name: str, record_id: int) -> bool:
        """
        Delete a record from the database

        Args:
            table_name: Name of the table
            record_id: ID of the record to delete

        Returns:
            True if the deletion was successful
        """
        cursor = self.conn.cursor()

        query = f"DELETE FROM {table_name} WHERE id = ?"
        cursor.execute(query, (record_id,))
        self.conn.commit()
        return cursor.rowcount > 0

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
        cursor = self.conn.cursor()

        operator = operator.upper()
        if operator not in ("AND", "OR"):
            raise ValueError("Operator must be 'AND' or 'OR'")

        where_conditions = []
        values = []

        for field, value in conditions.items():
            if value is None:
                where_conditions.append(f"{field} IS NULL")
            elif isinstance(value, str) and ("%" in value or "_" in value):
                where_conditions.append(f"{field} LIKE ?")
                values.append(value)
            else:
                where_conditions.append(f"{field} = ?")
                values.append(value)

        query = f"DELETE FROM {table_name}"

        if where_conditions:
            query += f" WHERE {f' {operator} '.join(where_conditions)}"

        cursor.execute(query, values)
        self.conn.commit()
        return cursor.rowcount > 0

    def get_all_records(self, table_name: str) -> List[Dict[str, Any]]:
        """
        Retrieve all records from the database

        Args:
            table_name: Name of the table

        Returns:
            List of dictionaries containing the records
        """
        cursor = self.conn.cursor()

        query = f"SELECT * FROM {table_name}"
        cursor.execute(query)
        records = cursor.fetchall()

        columns = self.get_column_names(table_name)
        return [dict(zip(columns, record)) for record in records]

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
            table_name: Name of the table to search
            conditions: Dictionary with the search criteria (e.g., {"name": "Mario", "age": 30})
            operator: Logical operator between conditions ("AND" or "OR")
            order_by: Field for sorting
            desc: If True, sort in descending order
            limit: Maximum number of results to return

        Returns:
            List of dictionaries containing the records that match the criteria
        """
        cursor = self.conn.cursor()

        operator = operator.upper()
        if operator not in ("AND", "OR"):
            raise ValueError("Operator must be 'AND' or 'OR'")

        where_conditions = []
        values = []

        for field, value in conditions.items():
            if value is None:
                where_conditions.append(f"{field} IS NULL")
            elif isinstance(value, str) and ("%" in value or "_" in value):
                where_conditions.append(f"{field} LIKE ?")
                values.append(value)
            else:
                where_conditions.append(f"{field} = ?")
                values.append(value)

        query = f"SELECT * FROM {table_name}"

        if where_conditions:
            query += f" WHERE {f' {operator} '.join(where_conditions)}"

        columns = self.get_column_names(table_name)
        if order_by:
            if order_by not in columns and order_by != "id":
                raise ValueError(f"Field '{order_by}' is not a valid column")
            query += f" ORDER BY {order_by} {'DESC' if desc else 'ASC'}"

        if limit:
            query += f" LIMIT {limit}"

        cursor.execute(query, values)
        records = cursor.fetchall()

        return [dict(zip(columns, record)) for record in records]

    def __del__(self):
        self.conn.close()
