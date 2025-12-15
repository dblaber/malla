"""PostgreSQL adapter implementation for database abstraction layer."""

from typing import Any, Sequence
from contextlib import contextmanager

try:
    import psycopg2
    import psycopg2.extras
    import psycopg2.extensions
except ImportError as e:
    raise ImportError(
        "psycopg2 is required for PostgreSQL support. "
        "Install it with: pip install psycopg2-binary"
    ) from e

from ..dialects.postgres_dialect import PostgresDialect


class PostgresCursor:
    """Wrapper for psycopg2 cursor providing unified interface.

    This class wraps the PostgreSQL cursor and ensures that:
    1. Results are returned as dictionaries (like SQLite adapter)
    2. Placeholder conversion from ? to %s happens automatically
    """

    def __init__(self, cursor: psycopg2.extras.RealDictCursor):
        """Initialize the cursor wrapper.

        Args:
            cursor: psycopg2 RealDictCursor instance
        """
        self._cursor = cursor

    def execute(self, query: str, params: Sequence[Any] | None = None) -> Any:
        """Execute a query with optional parameters.

        Automatically converts SQLite-style ? placeholders to PostgreSQL-style %s.

        Args:
            query: SQL query string (? or %s placeholders supported)
            params: Optional sequence of parameters

        Returns:
            The wrapped cursor for method chaining
        """
        # Convert SQLite-style ? placeholders to PostgreSQL-style %s
        query = query.replace("?", "%s")

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
        rows = self._cursor.fetchall()
        return [dict(row) for row in rows]

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


class PostgresAdapter:
    """Adapter for PostgreSQL database connections.

    This class wraps a psycopg2 connection and provides a consistent interface
    that matches the DatabaseAdapter protocol. It uses RealDictCursor for
    dict-like row access and provides access to the PostgreSQL dialect.
    """

    def __init__(self, conn: psycopg2.extensions.connection):
        """Initialize the PostgreSQL adapter.

        Args:
            conn: psycopg2 connection instance
        """
        self._conn = conn
        self._dialect = PostgresDialect()

    def cursor(self) -> PostgresCursor:
        """Get a cursor for executing queries.

        Returns:
            PostgresCursor instance wrapping RealDictCursor
        """
        # Use RealDictCursor for dict-based row access
        cursor = self._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        return PostgresCursor(cursor)

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
            PostgresCursor for executing queries within the transaction

        Example:
            with adapter.transaction() as cursor:
                cursor.execute("INSERT INTO ...")
                cursor.execute("UPDATE ...")
            # Auto-commits here if no exception
        """
        cursor = self._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        wrapped_cursor = PostgresCursor(cursor)
        try:
            yield wrapped_cursor
            self._conn.commit()
        except Exception:
            self._conn.rollback()
            raise
        finally:
            cursor.close()

    @property
    def dialect(self) -> PostgresDialect:
        """Get the SQL dialect for PostgreSQL.

        Returns:
            PostgresDialect instance for generating PostgreSQL-specific SQL
        """
        return self._dialect
