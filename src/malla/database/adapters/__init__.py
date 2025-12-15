"""Database adapters for different backends.

This package provides adapter classes that wrap native database connections
and provide a consistent interface across different database backends.
"""

from .protocol import DatabaseAdapter, DatabaseCursor
from .sqlite_adapter import SQLiteAdapter, SQLiteCursor

try:
    from .postgres_adapter import PostgresAdapter, PostgresCursor

    _POSTGRES_AVAILABLE = True
except ImportError:
    _POSTGRES_AVAILABLE = False
    PostgresAdapter = None  # type: ignore
    PostgresCursor = None  # type: ignore

__all__ = [
    "DatabaseAdapter",
    "DatabaseCursor",
    "SQLiteAdapter",
    "SQLiteCursor",
    "PostgresAdapter",
    "PostgresCursor",
]
