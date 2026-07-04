"""
OpportunityOS — Database Client
================================
Authorized by:
    MVP_SPEC.md, Section 2 (Repository Structure)
    ANTIGRAVITY_PROTOCOL.md, Rule 10.2, Round 1, Step [2]

Dependency: 05_CODE/db/init.sql (Step 1) must be applied before this module is used.

Responsibilities:
    - Initialize and manage a psycopg2 connection pool
    - Provide simple, safe query helpers for the pipeline and bot
    - Fail loud with full context on any DB error (ANTIGRAVITY_PROTOCOL Rule 6.2)

Intentionally NOT in this module:
    - No SQL queries (callers own their queries)
    - No schema knowledge (that lives in init.sql and schemas/opportunity.py)
    - No retry logic (the pipeline handles retries at a higher level)
    - No ORM (raw psycopg2 only — per project constraints)
"""

import logging
import os
from contextlib import contextmanager
from typing import Any, Generator

import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor, execute_values

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level pool. Initialized once at startup via init_pool().
# None until initialized — callers that call query helpers before init_pool()
# will receive a clear RuntimeError, not a cryptic AttributeError.
# ---------------------------------------------------------------------------
_pool: pool.ThreadedConnectionPool | None = None


# ---------------------------------------------------------------------------
# Pool lifecycle
# ---------------------------------------------------------------------------

def init_pool(minconn: int = 1, maxconn: int = 5) -> None:
    """
    Initialize the connection pool from DATABASE_URL environment variable.

    Call once at process startup — in run_pipeline.py and bot.py entry points.
    ThreadedConnectionPool is used because the bot and scheduler may run as
    separate processes, and within the bot, multiple commands could be handled
    concurrently by python-telegram-bot's executor.

    Raises:
        RuntimeError: If DATABASE_URL is not set.
        psycopg2.OperationalError: If the database is unreachable.
    """
    global _pool

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError(
            "[db] DATABASE_URL environment variable is not set. "
            "Copy .env.example to .env and fill in the value."
        )

    try:
        _pool = pool.ThreadedConnectionPool(minconn, maxconn, dsn=database_url)
        logger.info(f"[db] Connection pool initialized (min={minconn}, max={maxconn})")
    except psycopg2.OperationalError as e:
        logger.error(f"[db] Failed to connect to database: {e}")
        raise


def close_pool() -> None:
    """
    Close all connections in the pool. Call at process shutdown.
    Safe to call even if the pool was never initialized.
    """
    global _pool
    if _pool is not None:
        _pool.closeall()
        _pool = None
        logger.info("[db] Connection pool closed")


def is_ready() -> bool:
    """Return True if the pool has been initialized. Used in health checks."""
    return _pool is not None


# ---------------------------------------------------------------------------
# Connection context manager
# ---------------------------------------------------------------------------

@contextmanager
def get_connection() -> Generator[psycopg2.extensions.connection, None, None]:
    """
    Yield a connection from the pool. Commits on success, rolls back on error,
    and always returns the connection to the pool.

    Usage:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT ...")

    Raises:
        RuntimeError: If init_pool() has not been called.
        psycopg2.OperationalError: If no connections are available.
    """
    if _pool is None:
        raise RuntimeError(
            "[db] Connection pool not initialized. "
            "Call db.client.init_pool() before making queries."
        )

    conn = _pool.getconn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        _pool.putconn(conn)


# ---------------------------------------------------------------------------
# Query helpers
# ---------------------------------------------------------------------------

def execute(query: str, params: tuple | None = None) -> int:
    """
    Execute a DML statement (INSERT, UPDATE, DELETE) with no return value.
    Returns the number of rows affected.

    Args:
        query:  SQL string. Use %s placeholders (psycopg2 style).
        params: Tuple of values to bind. None for queries with no parameters.

    Returns:
        int: rowcount from the cursor.

    Raises:
        psycopg2.Error: On any database error. Caller is responsible for
                        logging the context (source, record ID, etc.).
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            return cur.rowcount


def execute_returning(query: str, params: tuple | None = None) -> dict[str, Any] | None:
    """
    Execute a DML statement that uses a RETURNING clause.
    Returns the first returned row as a dict, or None if nothing was returned.

    Typical use: INSERT ... RETURNING id
        row = execute_returning(
            "INSERT INTO opportunities (...) VALUES (...) RETURNING id",
            (...)
        )
        new_id = row["id"]

    Args:
        query:  SQL string with RETURNING clause.
        params: Tuple of values to bind.

    Returns:
        dict: The first returned row, or None.
    """
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            row = cur.fetchone()
            return dict(row) if row else None


def fetch_one(query: str, params: tuple | None = None) -> dict[str, Any] | None:
    """
    Execute a SELECT query and return the first row as a dict.
    Returns None if no rows match.

    Args:
        query:  SQL string.
        params: Tuple of values to bind.

    Returns:
        dict or None.
    """
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            row = cur.fetchone()
            return dict(row) if row else None


def fetch_all(query: str, params: tuple | None = None) -> list[dict[str, Any]]:
    """
    Execute a SELECT query and return all matching rows as a list of dicts.
    Returns an empty list if no rows match.

    Args:
        query:  SQL string.
        params: Tuple of values to bind.

    Returns:
        list[dict]: All matching rows.
    """
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            rows = cur.fetchall()
            return [dict(r) for r in rows]


def bulk_insert(query: str, rows: list[tuple]) -> int:
    """
    Bulk-insert multiple rows using psycopg2.extras.execute_values.
    Significantly faster than individual INSERT calls for large batches.

    The query must use %s as the VALUES placeholder:
        INSERT INTO opportunities (title, url, ...) VALUES %s

    Args:
        query:  SQL INSERT with %s placeholder for VALUES.
        rows:   List of tuples, one per row.

    Returns:
        int: Number of rows inserted (approximated via rowcount).

    Usage:
        bulk_insert(
            "INSERT INTO opportunities (title, url) VALUES %s",
            [("Title A", "https://..."), ("Title B", "https://...")]
        )
    """
    if not rows:
        return 0

    with get_connection() as conn:
        with conn.cursor() as cur:
            execute_values(cur, query, rows)
            return cur.rowcount


def url_hash_exists(url_hash: str) -> bool:
    """
    Check if a url_hash already exists in the opportunities table.
    Primary deduplication check — O(1) via the UNIQUE index on url_hash.

    This helper exists because deduplication is called on every item in
    every pipeline run. A named helper is clearer than an inline fetch_one.

    Args:
        url_hash: SHA-256 hex string (64 chars).

    Returns:
        bool: True if the hash already exists.
    """
    row = fetch_one(
        "SELECT 1 FROM opportunities WHERE url_hash = %s LIMIT 1",
        (url_hash,)
    )
    return row is not None
