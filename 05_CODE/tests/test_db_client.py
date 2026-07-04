"""
Tests for scheduler/db/client.py
=================================
Authorized by: ANTIGRAVITY_PROTOCOL.md, Rule 3 (Testing Requirements)
Coverage required: ANTIGRAVITY_PROTOCOL.md, Rule 3.2 — DB client tests

Rules applied:
    - All psycopg2 calls are mocked. No real DB connection is made.
    - Each test function tests exactly ONE behavior.
    - Naming convention: test_{what}_{when}_{expected}

Run with:
    pytest 05_CODE/tests/test_db_client.py -v
"""

import pytest
from unittest.mock import MagicMock, patch, call
import psycopg2

# Add scheduler directory to path so 'db.client' resolves to scheduler/db/client.py
import sys
import os
SCHEDULER_DIR = os.path.join(os.path.dirname(__file__), "..", "scheduler")
sys.path.insert(0, os.path.abspath(SCHEDULER_DIR))
from db import client


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_pool():
    """Reset the module-level pool before and after every test."""
    client._pool = None
    yield
    client._pool = None


@pytest.fixture
def mock_pool():
    """Return a mock ThreadedConnectionPool."""
    mock = MagicMock()
    client._pool = mock
    return mock


@pytest.fixture
def mock_connection(mock_pool):
    """Return a mock connection yielded by mock_pool.getconn()."""
    conn = MagicMock()
    mock_pool.getconn.return_value = conn
    return conn


@pytest.fixture
def mock_cursor(mock_connection):
    """Return a mock cursor from the mock connection."""
    cur = MagicMock()
    mock_connection.cursor.return_value.__enter__.return_value = cur
    return cur


# ---------------------------------------------------------------------------
# init_pool
# ---------------------------------------------------------------------------

def test_init_pool_raises_when_database_url_missing():
    """init_pool raises RuntimeError when DATABASE_URL env var is not set."""
    with patch.dict(os.environ, {}, clear=True):
        os.environ.pop("DATABASE_URL", None)
        with pytest.raises(RuntimeError, match="DATABASE_URL"):
            client.init_pool()


def test_init_pool_raises_when_database_unreachable():
    """init_pool raises psycopg2.OperationalError when DB is unreachable."""
    with patch.dict(os.environ, {"DATABASE_URL": "postgresql://bad/db"}):
        with patch("psycopg2.pool.ThreadedConnectionPool") as mock_cls:
            mock_cls.side_effect = psycopg2.OperationalError("connection refused")
            with pytest.raises(psycopg2.OperationalError):
                client.init_pool()


def test_init_pool_sets_global_pool_on_success():
    """init_pool sets the module-level _pool when connection succeeds."""
    with patch.dict(os.environ, {"DATABASE_URL": "postgresql://ok/db"}):
        with patch("psycopg2.pool.ThreadedConnectionPool") as mock_cls:
            fake_pool = MagicMock()
            mock_cls.return_value = fake_pool
            client.init_pool(minconn=1, maxconn=3)
            assert client._pool is fake_pool
            mock_cls.assert_called_once_with(1, 3, dsn="postgresql://ok/db")


# ---------------------------------------------------------------------------
# close_pool
# ---------------------------------------------------------------------------

def test_close_pool_calls_closeall_when_pool_exists(mock_pool):
    """close_pool calls closeall() and sets _pool to None."""
    client.close_pool()
    mock_pool.closeall.assert_called_once()
    assert client._pool is None


def test_close_pool_does_not_raise_when_pool_is_none():
    """close_pool is safe to call when pool was never initialized."""
    client._pool = None
    client.close_pool()  # Should not raise


# ---------------------------------------------------------------------------
# is_ready
# ---------------------------------------------------------------------------

def test_is_ready_returns_false_before_init():
    """is_ready returns False when pool has not been initialized."""
    assert client.is_ready() is False


def test_is_ready_returns_true_after_init(mock_pool):
    """is_ready returns True when pool is initialized."""
    assert client.is_ready() is True


# ---------------------------------------------------------------------------
# get_connection
# ---------------------------------------------------------------------------

def test_get_connection_raises_when_pool_not_initialized():
    """get_connection raises RuntimeError if called before init_pool."""
    client._pool = None
    with pytest.raises(RuntimeError, match="not initialized"):
        with client.get_connection():
            pass


def test_get_connection_commits_on_success(mock_pool, mock_connection):
    """get_connection commits the transaction when no exception occurs."""
    with client.get_connection() as conn:
        pass
    mock_connection.commit.assert_called_once()
    mock_connection.rollback.assert_not_called()


def test_get_connection_rolls_back_on_exception(mock_pool, mock_connection):
    """get_connection rolls back when an exception is raised inside the block."""
    with pytest.raises(ValueError):
        with client.get_connection():
            raise ValueError("something went wrong")
    mock_connection.rollback.assert_called_once()
    mock_connection.commit.assert_not_called()


def test_get_connection_returns_conn_to_pool_on_success(mock_pool, mock_connection):
    """get_connection always calls putconn after use, even on success."""
    with client.get_connection():
        pass
    mock_pool.putconn.assert_called_once_with(mock_connection)


def test_get_connection_returns_conn_to_pool_on_exception(mock_pool, mock_connection):
    """get_connection always calls putconn after use, even on exception."""
    with pytest.raises(RuntimeError):
        with client.get_connection():
            raise RuntimeError("test error")
    mock_pool.putconn.assert_called_once_with(mock_connection)


# ---------------------------------------------------------------------------
# execute
# ---------------------------------------------------------------------------

def test_execute_runs_query_and_returns_rowcount(mock_pool, mock_connection, mock_cursor):
    """execute runs the query and returns the cursor rowcount."""
    mock_cursor.rowcount = 1
    result = client.execute("UPDATE opportunities SET score = %s WHERE id = %s", (80, 1))
    mock_cursor.execute.assert_called_once_with(
        "UPDATE opportunities SET score = %s WHERE id = %s", (80, 1)
    )
    assert result == 1


def test_execute_with_no_params(mock_pool, mock_connection, mock_cursor):
    """execute works correctly when params is None."""
    mock_cursor.rowcount = 4
    result = client.execute("DELETE FROM pipeline_runs WHERE status = 'failed'", None)
    mock_cursor.execute.assert_called_once_with(
        "DELETE FROM pipeline_runs WHERE status = 'failed'", None
    )
    assert result == 4


# ---------------------------------------------------------------------------
# execute_returning
# ---------------------------------------------------------------------------

def test_execute_returning_returns_dict_on_match(mock_pool, mock_connection):
    """execute_returning returns the first row as a dict when a row is returned."""
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = {"id": 42}
    mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
    result = client.execute_returning(
        "INSERT INTO opportunities (title) VALUES (%s) RETURNING id", ("Test",)
    )
    assert result == {"id": 42}


def test_execute_returning_returns_none_when_no_rows(mock_pool, mock_connection):
    """execute_returning returns None when no rows are returned by RETURNING clause."""
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = None
    mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
    result = client.execute_returning(
        "INSERT INTO opportunities (title) VALUES (%s) RETURNING id", ("Test",)
    )
    assert result is None


# ---------------------------------------------------------------------------
# fetch_one
# ---------------------------------------------------------------------------

def test_fetch_one_returns_dict_when_row_found(mock_pool, mock_connection):
    """fetch_one returns a dict when a matching row exists."""
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = {"id": 1, "source": "github"}
    mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
    result = client.fetch_one("SELECT * FROM opportunities WHERE id = %s", (1,))
    assert result == {"id": 1, "source": "github"}


def test_fetch_one_returns_none_when_no_row(mock_pool, mock_connection):
    """fetch_one returns None when no matching row exists."""
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = None
    mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
    result = client.fetch_one("SELECT * FROM opportunities WHERE id = %s", (999,))
    assert result is None


# ---------------------------------------------------------------------------
# fetch_all
# ---------------------------------------------------------------------------

def test_fetch_all_returns_list_of_dicts(mock_pool, mock_connection):
    """fetch_all returns a list of dicts for all matching rows."""
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = [
        {"source": "github", "score": 85},
        {"source": "arxiv", "score": 70},
    ]
    mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
    result = client.fetch_all("SELECT source, score FROM opportunities ORDER BY score DESC")
    assert len(result) == 2
    assert result[0]["source"] == "github"
    assert result[1]["score"] == 70


def test_fetch_all_returns_empty_list_when_no_rows(mock_pool, mock_connection):
    """fetch_all returns an empty list when no rows match."""
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = []
    mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
    result = client.fetch_all("SELECT * FROM opportunities WHERE score > %s", (100,))
    assert result == []


# ---------------------------------------------------------------------------
# bulk_insert
# ---------------------------------------------------------------------------

def test_bulk_insert_returns_zero_for_empty_rows(mock_pool):
    """bulk_insert returns 0 immediately without hitting DB when rows is empty."""
    result = client.bulk_insert("INSERT INTO opportunities (title) VALUES %s", [])
    assert result == 0
    # Pool should not have been touched
    mock_pool.getconn.assert_not_called()


def test_bulk_insert_calls_execute_values(mock_pool, mock_connection):
    """bulk_insert calls psycopg2.extras.execute_values with correct args."""
    mock_cursor = MagicMock()
    mock_cursor.rowcount = 2
    mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
    rows = [("Title A", "https://a.com"), ("Title B", "https://b.com")]
    with patch("db.client.execute_values") as mock_ev:
        result = client.bulk_insert(
            "INSERT INTO opportunities (title, url) VALUES %s", rows
        )
        mock_ev.assert_called_once_with(mock_cursor, "INSERT INTO opportunities (title, url) VALUES %s", rows)


# ---------------------------------------------------------------------------
# url_hash_exists
# ---------------------------------------------------------------------------

def test_url_hash_exists_returns_true_when_hash_found(mock_pool, mock_connection):
    """url_hash_exists returns True when the hash is already in the DB."""
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = {"1": 1}
    mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
    result = client.url_hash_exists("a" * 64)
    assert result is True


def test_url_hash_exists_returns_false_when_hash_not_found(mock_pool, mock_connection):
    """url_hash_exists returns False when the hash is not in the DB."""
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = None
    mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
    result = client.url_hash_exists("b" * 64)
    assert result is False
