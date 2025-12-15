"""Connection pooling for PostgreSQL database connections."""

import logging
import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from malla.config import AppConfig

try:
    import psycopg2
    import psycopg2.pool
    import psycopg2.extensions
except ImportError:
    # PostgreSQL support is optional - only imported when needed
    psycopg2 = None  # type: ignore

logger = logging.getLogger(__name__)


class PostgresConnectionPool:
    """Thread-safe connection pool for PostgreSQL.

    This class manages a pool of PostgreSQL connections using psycopg2's
    ThreadedConnectionPool. It ensures efficient connection reuse and
    proper resource management.
    """

    def __init__(self, config: "AppConfig"):
        """Initialize the connection pool (lazy initialization).

        Args:
            config: Application configuration with PostgreSQL settings
        """
        self._config = config
        self._pool: psycopg2.pool.ThreadedConnectionPool | None = None
        self._lock = threading.Lock()

    def initialize(self) -> None:
        """Initialize the connection pool.

        Creates the underlying ThreadedConnectionPool with configured settings.
        This method is idempotent - subsequent calls have no effect.

        Raises:
            ImportError: If psycopg2 is not installed
            psycopg2.Error: If connection to PostgreSQL fails
        """
        if psycopg2 is None:
            raise ImportError(
                "psycopg2 is required for PostgreSQL connection pooling. "
                "Install it with: pip install psycopg2-binary"
            )

        with self._lock:
            if self._pool is not None:
                return

            logger.info(
                f"Initializing PostgreSQL connection pool to "
                f"{self._config.postgres_host}:{self._config.postgres_port}/"
                f"{self._config.postgres_database}"
            )

            self._pool = psycopg2.pool.ThreadedConnectionPool(
                minconn=self._config.postgres_pool_min,
                maxconn=self._config.postgres_pool_max,
                host=self._config.postgres_host,
                port=self._config.postgres_port,
                database=self._config.postgres_database,
                user=self._config.postgres_user,
                password=self._config.postgres_password,
                sslmode=self._config.postgres_ssl_mode,
            )

            logger.info(
                f"PostgreSQL connection pool initialized "
                f"(min={self._config.postgres_pool_min}, "
                f"max={self._config.postgres_pool_max})"
            )

    def get_connection(self) -> "psycopg2.extensions.connection":
        """Get a connection from the pool.

        Returns:
            psycopg2 connection instance

        Raises:
            RuntimeError: If pool is not initialized
            psycopg2.pool.PoolError: If pool is exhausted
        """
        if self._pool is None:
            self.initialize()

        if self._pool is None:
            raise RuntimeError("Failed to initialize PostgreSQL connection pool")

        return self._pool.getconn()

    def put_connection(self, conn: "psycopg2.extensions.connection") -> None:
        """Return a connection to the pool.

        Args:
            conn: Connection to return to the pool
        """
        if self._pool is not None:
            self._pool.putconn(conn)

    def close_all(self) -> None:
        """Close all connections in the pool.

        This should be called during application shutdown to properly
        release database resources.
        """
        with self._lock:
            if self._pool is not None:
                self._pool.closeall()
                self._pool = None
                logger.info("Closed PostgreSQL connection pool")


# Global pool instance (singleton per process)
_postgres_pool: PostgresConnectionPool | None = None
_pool_lock = threading.Lock()


def get_postgres_pool(config: "AppConfig") -> PostgresConnectionPool:
    """Get or create the global PostgreSQL connection pool.

    This function implements a singleton pattern for the connection pool,
    ensuring only one pool exists per Python process.

    Args:
        config: Application configuration with PostgreSQL settings

    Returns:
        PostgresConnectionPool instance
    """
    global _postgres_pool

    with _pool_lock:
        if _postgres_pool is None:
            _postgres_pool = PostgresConnectionPool(config)
            _postgres_pool.initialize()
        return _postgres_pool


def close_postgres_pool() -> None:
    """Close the global PostgreSQL connection pool.

    Call this during application shutdown to properly release resources.
    """
    global _postgres_pool

    with _pool_lock:
        if _postgres_pool is not None:
            _postgres_pool.close_all()
            _postgres_pool = None
