"""SQLite-specific SQL dialect implementation."""


class SQLiteDialect:
    """SQLite SQL dialect for generating database-specific SQL expressions.

    This class provides SQLite-specific implementations of common SQL operations
    that differ between database backends.
    """

    def to_hex(self, column: str, format: str = "!%08x") -> str:
        """Convert integer to hex string using SQLite's printf function.

        Args:
            column: Column name or expression to convert
            format: Printf-style format string (default: "!%08x")

        Returns:
            SQL expression: printf('!%08x', column)
        """
        return f"printf('{format}', {column})"

    def from_unixepoch(self, column: str) -> str:
        """Convert unix timestamp to datetime using SQLite's datetime function.

        Args:
            column: Column name or expression containing unix timestamp

        Returns:
            SQL expression: datetime(column, 'unixepoch')
        """
        return f"datetime({column}, 'unixepoch')"

    def strftime_hour(self, column: str) -> str:
        """Extract hour from unix timestamp using SQLite's strftime.

        Args:
            column: Column name or expression containing unix timestamp

        Returns:
            SQL expression: strftime('%H', datetime(column, 'unixepoch'))
        """
        return f"strftime('%H', datetime({column}, 'unixepoch'))"

    def autoincrement_column(self) -> str:
        """Return SQLite autoincrement primary key definition.

        Returns:
            "INTEGER PRIMARY KEY AUTOINCREMENT"
        """
        return "INTEGER PRIMARY KEY AUTOINCREMENT"

    def blob_type(self) -> str:
        """Return SQLite binary data type.

        Returns:
            "BLOB"
        """
        return "BLOB"

    def current_timestamp(self) -> str:
        """Return SQL expression for current unix timestamp.

        Returns:
            SQL expression: strftime('%s', 'now')
        """
        return "strftime('%s', 'now')"

    def pragma_statements(self) -> list[str]:
        """Return SQLite PRAGMA statements for optimal configuration.

        Returns:
            List of PRAGMA statements for:
            - WAL journal mode for better concurrency
            - NORMAL synchronous mode for performance
            - 30-second busy timeout
            - Foreign key constraints enabled
            - 10MB cache size
            - Memory temp storage
        """
        return [
            "PRAGMA journal_mode=WAL",
            "PRAGMA synchronous=NORMAL",
            "PRAGMA busy_timeout=30000",  # 30 seconds
            "PRAGMA foreign_keys=ON",
            "PRAGMA cache_size=10000",  # 10MB cache
            "PRAGMA temp_store=MEMORY",
        ]
