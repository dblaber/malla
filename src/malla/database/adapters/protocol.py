"""Protocol definitions for database adapters.

This module defines the interfaces that database adapters must implement
to provide a consistent API across different database backends (SQLite, PostgreSQL, etc.).
"""

from typing import Any, Protocol, Sequence
from contextlib import contextmanager


class DatabaseCursor(Protocol):
    """Protocol for database cursor objects.

    Provides a unified interface for executing queries and fetching results
    across different database backends.
    """

    def execute(self, query: str, params: Sequence[Any] | None = None) -> Any:
        """Execute a query with optional parameters.

        Args:
            query: SQL query string (may use ? or %s placeholders depending on backend)
            params: Optional sequence of parameters to substitute into query

        Returns:
            Database-specific cursor result
        """
        ...

    def fetchone(self) -> dict[str, Any] | None:
        """Fetch one row as a dictionary.

        Returns:
            Dictionary mapping column names to values, or None if no more rows
        """
        ...

    def fetchall(self) -> list[dict[str, Any]]:
        """Fetch all rows as list of dictionaries.

        Returns:
            List of dictionaries, each mapping column names to values
        """
        ...

    def close(self) -> None:
        """Close the cursor and free resources."""
        ...

    @property
    def rowcount(self) -> int:
        """Number of rows affected by the last operation."""
        ...


class DatabaseAdapter(Protocol):
    """Protocol for database connection adapters.

    Provides a unified interface for database connections across different
    backends. Each adapter wraps the native connection object and provides
    consistent access patterns.
    """

    def cursor(self) -> DatabaseCursor:
        """Get a cursor for executing queries.

        Returns:
            DatabaseCursor instance for this connection
        """
        ...

    def commit(self) -> None:
        """Commit the current transaction."""
        ...

    def rollback(self) -> None:
        """Rollback the current transaction."""
        ...

    def close(self) -> None:
        """Close the connection and free resources."""
        ...

    @contextmanager
    def transaction(self):
        """Context manager for explicit transaction management.

        Usage:
            with conn.transaction():
                cursor.execute("INSERT INTO ...")
                cursor.execute("UPDATE ...")
            # Auto-commits on success, auto-rollbacks on exception
        """
        ...

    @property
    def dialect(self) -> "SQLDialect":  # type: ignore[name-defined]
        """Get the SQL dialect for this adapter.

        Returns:
            SQLDialect instance providing database-specific SQL generation
        """
        ...


# Import SQLDialect type for type checking
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..dialects.protocol import SQLDialect
