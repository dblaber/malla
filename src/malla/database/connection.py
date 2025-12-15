"""
Database connection management for Meshtastic Mesh Health Web UI.
"""

import logging
import os
import sqlite3
from typing import TYPE_CHECKING

# Prefer configuration loader over environment variables
from malla.config import get_config
from .adapters.sqlite_adapter import SQLiteAdapter

try:
    from .adapters.postgres_adapter import PostgresAdapter
    from .pool import get_postgres_pool

    _POSTGRES_AVAILABLE = True
except ImportError:
    _POSTGRES_AVAILABLE = False
    PostgresAdapter = None  # type: ignore
    get_postgres_pool = None  # type: ignore

if TYPE_CHECKING:
    from .adapters.protocol import DatabaseAdapter

logger = logging.getLogger(__name__)


def get_db_connection() -> "DatabaseAdapter":
    """
    Get a database connection based on configuration.

    Returns appropriate adapter (SQLite or PostgreSQL) based on the
    database_type configuration setting.

    Returns:
        DatabaseAdapter: Database connection adapter with dialect support
    """
    config = get_config()
    db_type = config.database_type.lower()

    if db_type == "sqlite":
        return _get_sqlite_connection()
    elif db_type == "postgres":
        if not _POSTGRES_AVAILABLE:
            raise ImportError(
                "PostgreSQL support requires psycopg2. "
                "Install it with: pip install psycopg2-binary"
            )
        return _get_postgres_connection()
    else:
        raise ValueError(
            f"Unsupported database type: {db_type}. "
            f"Supported types: 'sqlite', 'postgres'"
        )


def _get_sqlite_connection() -> SQLiteAdapter:
    """Get a SQLite connection wrapped in adapter.

    Returns:
        SQLiteAdapter: Adapter wrapping sqlite3.Connection
    """
    config = get_config()

    # Resolve DB path:
    # 1. Explicit override via `MALLA_DATABASE_FILE` env-var (handy for scripts)
    # 2. Value from YAML configuration
    # 3. Fallback to hard-coded default

    db_path: str = (
        os.getenv("MALLA_DATABASE_FILE")
        or config.database_file
        or "meshtastic_history.db"
    )

    try:
        conn = sqlite3.connect(
            db_path, timeout=30.0
        )  # 30 second timeout for busy database
        conn.row_factory = sqlite3.Row  # Enable column access by name

        adapter = SQLiteAdapter(conn)
        cursor = adapter.cursor()

        # Apply SQLite-specific PRAGMA statements
        for pragma in adapter.dialect.pragma_statements():
            cursor.execute(pragma)

        # ------------------------------------------------------------------
        # Lightweight schema migrations – run once per connection.
        # ------------------------------------------------------------------
        try:
            _ensure_schema_migrations(cursor)
        except Exception as e:
            logger.warning(f"Schema migration check failed: {e}")

        return adapter
    except Exception as e:
        logger.error(f"Failed to connect to SQLite database: {e}")
        raise


def _get_postgres_connection() -> "PostgresAdapter":
    """Get a PostgreSQL connection from pool wrapped in adapter.

    Returns:
        PostgresAdapter: Adapter wrapping psycopg2 connection from pool
    """
    config = get_config()

    try:
        # Get connection from pool
        pool = get_postgres_pool(config)
        conn = pool.get_connection()

        adapter = PostgresAdapter(conn)
        cursor = adapter.cursor()

        # Run schema migrations
        try:
            _ensure_schema_migrations(cursor)
        except Exception as e:
            logger.warning(f"Schema migration check failed: {e}")

        return adapter
    except Exception as e:
        logger.error(f"Failed to connect to PostgreSQL database: {e}")
        raise


def init_database() -> None:
    """
    Initialize the database connection and verify it's accessible.
    This function is called during application startup.
    """
    config = get_config()
    db_type = config.database_type.lower()

    if db_type == "sqlite":
        db_path = (
            os.getenv("MALLA_DATABASE_FILE")
            or config.database_file
            or "meshtastic_history.db"
        )
        logger.info(f"Initializing SQLite database connection to: {db_path}")
    else:
        logger.info(f"Initializing {db_type} database connection")

    try:
        # Test the connection
        adapter = get_db_connection()
        cursor = adapter.cursor()

        # Database-specific verification query
        if db_type == "sqlite":
            cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
            result = cursor.fetchone()
            table_count = result["COUNT(*)"] if result else 0

            # Check and log the journal mode
            cursor.execute("PRAGMA journal_mode")
            result = cursor.fetchone()
            journal_mode = result["journal_mode"] if result else "unknown"

            logger.info(
                f"SQLite database connection successful - "
                f"found {table_count} tables, journal_mode: {journal_mode}"
            )
        else:  # postgres
            cursor.execute(
                "SELECT COUNT(*) FROM information_schema.tables "
                "WHERE table_schema = 'public'"
            )
            result = cursor.fetchone()
            table_count = result["count"] if result else 0

            logger.info(
                f"PostgreSQL database connection successful - found {table_count} tables"
            )

        adapter.close()

    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        # Don't raise the exception - let the app start anyway
        # The database might not exist yet or be created by another process


# ----------------------------------------------------------------------
# Internal helpers
# ----------------------------------------------------------------------


_SCHEMA_MIGRATIONS_DONE: set[str] = set()


def _ensure_schema_migrations(cursor) -> None:
    """Run any idempotent schema updates that the application depends on.

    Currently this checks that ``node_info`` has a ``primary_channel`` column
    (added in April 2024) so queries that reference it do not fail when the
    database was created with an older version of the schema.

    The function is **safe** to run repeatedly – it will only attempt each
    migration once per Python process and each individual migration is
    guarded with a try/except that ignores the *duplicate column* error.

    Args:
        cursor: Database cursor from adapter (SQLiteCursor or PostgresCursor)
    """

    global _SCHEMA_MIGRATIONS_DONE  # pylint: disable=global-statement

    # Quickly short-circuit if we've already handled migrations in this process
    if "primary_channel" in _SCHEMA_MIGRATIONS_DONE:
        return

    try:
        config = get_config()
        db_type = config.database_type.lower()

        # Check whether the column already exists (database-specific query)
        if db_type == "sqlite":
            cursor.execute("PRAGMA table_info(node_info)")
            columns = [row["name"] for row in cursor.fetchall()]
        else:  # postgres
            cursor.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'node_info'
                """
            )
            columns = [row["column_name"] for row in cursor.fetchall()]

        if "primary_channel" not in columns:
            cursor.execute("ALTER TABLE node_info ADD COLUMN primary_channel TEXT")
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_node_primary_channel ON node_info(primary_channel)"
            )
            logging.info(
                "Added primary_channel column to node_info table via auto-migration"
            )

        _SCHEMA_MIGRATIONS_DONE.add("primary_channel")
    except Exception as exc:
        # Ignore errors about duplicate columns in race situations – another
        # process may have altered the table first.
        error_msg = str(exc).lower()
        if "duplicate column" in error_msg or "already exists" in error_msg:
            _SCHEMA_MIGRATIONS_DONE.add("primary_channel")
        else:
            raise
