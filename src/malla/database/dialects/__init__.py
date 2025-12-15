"""SQL dialects for different database backends.

This package provides dialect classes that generate database-specific SQL
expressions and handle schema differences between backends.
"""

from .protocol import SQLDialect
from .sqlite_dialect import SQLiteDialect

try:
    from .postgres_dialect import PostgresDialect

    _POSTGRES_AVAILABLE = True
except ImportError:
    _POSTGRES_AVAILABLE = False
    PostgresDialect = None  # type: ignore

__all__ = [
    "SQLDialect",
    "SQLiteDialect",
    "PostgresDialect",
]
