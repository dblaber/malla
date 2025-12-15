"""SQLite adapter implementation for database abstraction layer."""

import sqlite3
from typing import Any, Sequence
from contextlib import contextmanager

from ..dialects.sqlite_dialect import SQLiteDialect


class SQLiteCursor:
    """Wrapper for sqlite3.Cursor providing dict-based row access.

    This class wraps the native SQLite cursor and ensures that results
    are always returned as dictionaries, maintaining consistency with
    the DatabaseCursor protocol.
    """

    def __init__(self, cursor: sqlite3.Cursor):
        """Initialize the cursor wrapper.

        Args:
            cursor: Native sqlite3.Cursor instance
        """
        self._cursor = cursor

    def execute(self, query: str, params: Sequence[Any] | None = None) -> Any:
        """Execute a query with optional parameters.

        Args:
            query: SQL query string with ? placeholders
            params: Optional sequence of parameters

        Returns:
            The wrapped cursor for method chaining
        """
        if params is None:
            return self._cursor.execute(query)
        return self._cursor.execute(query, params)

    def fetchone(self) -> dict[str, Any] | None:
        """Fetch one row as a dictionary.

        Returns:
            Dictionary mapping column names to values, or None if no more rows
        """
        row = self._cursor.fetchone()
        return dict(row) if row else None

    def fetchall(self) -> list[dict[str, Any]]:
        """Fetch all rows as list of dictionaries.

        Returns:
            List of dictionaries, each mapping column names to values
        """
        return [dict(row) for row in self._cursor.fetchall()]

    def close(self) -> None:
        """Close the cursor and free resources."""
        self._cursor.close()

    @property
    def rowcount(self) -> int:
        """Number of rows affected by the last operation.

        Returns:
            Row count from the underlying cursor
        """
        return self._cursor.rowcount


class SQLiteAdapter:
    """Adapter for SQLite database connections.

    This class wraps a sqlite3.Connection and provides a consistent interface
    that matches the DatabaseAdapter protocol. It ensures row factory is set
    and provides access to the SQLite dialect for SQL generation.
    """

    def __init__(self, conn: sqlite3.Connection):
        """Initialize the SQLite adapter.

        Args:
            conn: Native sqlite3.Connection instance
        """
        self._conn = conn
        self._dialect = SQLiteDialect()
        # Ensure row factory is set for dict-like access
        self._conn.row_factory = sqlite3.Row

    def cursor(self) -> SQLiteCursor:
        """Get a cursor for executing queries.

        Returns:
            SQLiteCursor instance wrapping the native cursor
        """
        return SQLiteCursor(self._conn.cursor())

    def commit(self) -> None:
        """Commit the current transaction."""
        self._conn.commit()

    def rollback(self) -> None:
        """Rollback the current transaction."""
        self._conn.rollback()

    def close(self) -> None:
        """Close the connection and free resources."""
        self._conn.close()

    @contextmanager
    def transaction(self):
        """Context manager for explicit transaction management.

        Yields a cursor and automatically commits on success or rolls back
        on exception.

        Yields:
            SQLiteCursor for executing queries within the transaction

        Example:
            with adapter.transaction() as cursor:
                cursor.execute("INSERT INTO ...")
                cursor.execute("UPDATE ...")
            # Auto-commits here if no exception
        """
        cursor = self._conn.cursor()
        wrapped_cursor = SQLiteCursor(cursor)
        try:
            yield wrapped_cursor
            self._conn.commit()
        except Exception:
            self._conn.rollback()
            raise
        finally:
            cursor.close()

    @property
    def dialect(self) -> SQLiteDialect:
        """Get the SQL dialect for SQLite.

        Returns:
            SQLiteDialect instance for generating SQLite-specific SQL
        """
        return self._dialect
