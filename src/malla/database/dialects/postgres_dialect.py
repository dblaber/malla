"""PostgreSQL-specific SQL dialect implementation."""


class PostgresDialect:
    """PostgreSQL SQL dialect for generating database-specific SQL expressions.

    This class provides PostgreSQL-specific implementations of common SQL operations
    that differ between database backends.
    """

    def to_hex(self, column: str, format: str = "!%08x") -> str:
        """Convert integer to hex string using PostgreSQL's TO_HEX function.

        Args:
            column: Column name or expression to convert
            format: Printf-style format string (default: "!%08x" for 8-char hex with ! prefix)

        Returns:
            SQL expression: '!' || LPAD(TO_HEX(column), 8, '0')

        Note:
            The format parameter is parsed to extract padding width. Only the numeric
            portion is used (e.g., "!%08x" -> 8 characters padding).
        """
        # Extract padding from format string (e.g., "!%08x" -> 8)
        # For simplicity, assume standard format and use 8 characters
        padding = 8
        if format and "%" in format:
            # Try to extract number between % and x
            try:
                import re

                match = re.search(r"%0?(\d+)[xX]", format)
                if match:
                    padding = int(match.group(1))
            except (ValueError, AttributeError):
                pass

        # PostgreSQL: '!' || LPAD(TO_HEX(column), 8, '0')
        return f"'!' || LPAD(TO_HEX({column}), {padding}, '0')"

    def from_unixepoch(self, column: str) -> str:
        """Convert unix timestamp to datetime using PostgreSQL's TO_TIMESTAMP function.

        Args:
            column: Column name or expression containing unix timestamp

        Returns:
            SQL expression: TO_TIMESTAMP(column)
        """
        return f"TO_TIMESTAMP({column})"

    def strftime_hour(self, column: str) -> str:
        """Extract hour from unix timestamp using PostgreSQL's EXTRACT function.

        Args:
            column: Column name or expression containing unix timestamp

        Returns:
            SQL expression: EXTRACT(HOUR FROM TO_TIMESTAMP(column))
        """
        return f"EXTRACT(HOUR FROM TO_TIMESTAMP({column}))"

    def autoincrement_column(self) -> str:
        """Return PostgreSQL autoincrement primary key definition.

        Returns:
            "SERIAL PRIMARY KEY"
        """
        return "SERIAL PRIMARY KEY"

    def blob_type(self) -> str:
        """Return PostgreSQL binary data type.

        Returns:
            "BYTEA"
        """
        return "BYTEA"

    def current_timestamp(self) -> str:
        """Return SQL expression for current unix timestamp.

        Returns:
            SQL expression: EXTRACT(EPOCH FROM NOW())
        """
        return "EXTRACT(EPOCH FROM NOW())"

    def pragma_statements(self) -> list[str]:
        """Return PostgreSQL initialization statements.

        PostgreSQL doesn't use PRAGMA statements like SQLite.
        Configuration is typically done server-side or via SET commands.

        Returns:
            Empty list (no initialization statements needed)
        """
        return []
