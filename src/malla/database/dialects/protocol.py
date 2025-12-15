"""Protocol definitions for SQL dialects.

This module defines the interface for SQL dialect classes that generate
database-specific SQL expressions and handle schema differences between
database backends.
"""

from typing import Protocol


class SQLDialect(Protocol):
    """Protocol for SQL dialect-specific query generation.

    Each database backend (SQLite, PostgreSQL, etc.) implements this protocol
    to provide database-specific SQL syntax for common operations.
    """

    def to_hex(self, column: str, format: str = "!%08x") -> str:
        """Convert integer node_id column to hex string format.

        Args:
            column: Column name or expression to convert
            format: Printf-style format string (default: "!%08x" for 8-char hex with ! prefix)

        Returns:
            SQL expression that converts the integer to formatted hex string

        Examples:
            SQLite: printf('!%08x', node_id)
            PostgreSQL: '!' || LPAD(TO_HEX(node_id), 8, '0')
        """
        ...

    def from_unixepoch(self, column: str) -> str:
        """Convert unix timestamp column to datetime.

        Args:
            column: Column name or expression containing unix timestamp

        Returns:
            SQL expression that converts unix timestamp to datetime

        Examples:
            SQLite: datetime(timestamp, 'unixepoch')
            PostgreSQL: TO_TIMESTAMP(timestamp)
        """
        ...

    def strftime_hour(self, column: str) -> str:
        """Extract hour from unix timestamp column.

        Args:
            column: Column name or expression containing unix timestamp

        Returns:
            SQL expression that extracts hour (0-23) from timestamp

        Examples:
            SQLite: strftime('%H', datetime(timestamp, 'unixepoch'))
            PostgreSQL: EXTRACT(HOUR FROM TO_TIMESTAMP(timestamp))
        """
        ...

    def autoincrement_column(self) -> str:
        """Return SQL definition for autoincrement primary key column.

        Returns:
            SQL type definition for autoincrement primary key

        Examples:
            SQLite: "INTEGER PRIMARY KEY AUTOINCREMENT"
            PostgreSQL: "SERIAL PRIMARY KEY"
        """
        ...

    def blob_type(self) -> str:
        """Return SQL type name for binary data.

        Returns:
            SQL type name for binary/blob data

        Examples:
            SQLite: "BLOB"
            PostgreSQL: "BYTEA"
        """
        ...

    def current_timestamp(self) -> str:
        """Return SQL expression for current unix timestamp.

        Returns:
            SQL expression that evaluates to current timestamp as unix epoch

        Examples:
            SQLite: "strftime('%s', 'now')"
            PostgreSQL: "EXTRACT(EPOCH FROM NOW())"
        """
        ...

    def pragma_statements(self) -> list[str]:
        """Return database-specific initialization statements.

        Returns:
            List of SQL statements to execute on connection initialization
            (e.g., PRAGMA statements for SQLite, empty list for PostgreSQL)

        Examples:
            SQLite: ["PRAGMA journal_mode=WAL", "PRAGMA foreign_keys=ON", ...]
            PostgreSQL: []
        """
        ...
