"""
Tests for scheduler/analytics/outcomes.py
=========================================
Authorized by: ANTIGRAVITY_PROTOCOL.md, Rule 3 (Testing Requirements)
"""

import os
import sys
from unittest.mock import patch, mock_open, ANY

import pytest

# Ensure scheduler package is discoverable
SCHEDULER_DIR = os.path.join(os.path.dirname(__file__), "..", "scheduler")
sys.path.insert(0, os.path.abspath(SCHEDULER_DIR))

from analytics.outcomes import (
    get_outcomes_by_source,
    get_outcomes_by_type,
    get_outcomes_by_tag,
    get_outcomes_by_tech,
    get_outcomes_by_domain,
    generate_weekly_report,
    write_weekly_report,
)


@pytest.fixture
def mock_db_client():
    with patch("analytics.outcomes.db_client") as m_db:
        yield m_db


def test_get_outcomes_by_source(mock_db_client):
    mock_db_client.fetch_all.return_value = [{"source": "github", "saved": 1, "building": 0, "applied": 0, "won": 0, "wrong": 0}]
    res = get_outcomes_by_source()
    assert len(res) == 1
    assert res[0]["source"] == "github"
    mock_db_client.fetch_all.assert_called_once()


def test_get_outcomes_by_type(mock_db_client):
    mock_db_client.fetch_all.return_value = [{"opportunity_type": "tool", "saved": 1, "building": 0, "applied": 0, "won": 0, "wrong": 0}]
    res = get_outcomes_by_type()
    assert len(res) == 1
    assert res[0]["opportunity_type"] == "tool"


def test_get_outcomes_by_tag(mock_db_client):
    mock_db_client.fetch_all.return_value = [{"tag": "ai", "saved": 1, "building": 0, "applied": 0, "won": 0, "wrong": 0}]
    res = get_outcomes_by_tag(limit=5)
    assert len(res) == 1
    mock_db_client.fetch_all.assert_called_once_with(ANY, (5,))


def test_get_outcomes_by_tech(mock_db_client):
    mock_db_client.fetch_all.return_value = [{"tech": "python", "saved": 1, "building": 0, "applied": 0, "won": 0, "wrong": 0}]
    res = get_outcomes_by_tech(limit=5)
    assert len(res) == 1
    mock_db_client.fetch_all.assert_called_once_with(ANY, (5,))


def test_get_outcomes_by_domain(mock_db_client):
    mock_db_client.fetch_all.return_value = [{"domain": "llm", "saved": 1, "building": 0, "applied": 0, "won": 0, "wrong": 0}]
    res = get_outcomes_by_domain(limit=5)
    assert len(res) == 1
    mock_db_client.fetch_all.assert_called_once_with(ANY, (5,))


def test_generate_weekly_report(mock_db_client):
    # Mock return values for get_outcomes_by_source, get_outcomes_by_type, etc.
    mock_db_client.fetch_all.side_effect = [
        [{"source": "github", "saved": 1, "building": 2, "applied": 3, "won": 4, "wrong": 5}],
        [{"opportunity_type": "tool", "saved": 1, "building": 2, "applied": 3, "won": 4, "wrong": 5}],
        [{"tag": "ai", "saved": 1, "building": 2, "applied": 3, "won": 4, "wrong": 5}],
        [{"tech": "python", "saved": 1, "building": 2, "applied": 3, "won": 4, "wrong": 5}],
        [{"domain": "llm", "saved": 1, "building": 2, "applied": 3, "won": 4, "wrong": 5}],
    ]
    
    report = generate_weekly_report()
    assert "# WEEKLY OUTCOME ANALYTICS REPORT" in report
    assert "github" in report
    assert "tool" in report
    assert "ai" in report
    assert "python" in report
    assert "llm" in report
    assert mock_db_client.fetch_all.call_count == 5


def test_write_weekly_report(mock_db_client):
    mock_db_client.is_ready.return_value = False
    mock_db_client.fetch_all.return_value = []
    
    m_open = mock_open()
    with patch("builtins.open", m_open):
        write_weekly_report("dummy.md")
        
    m_open.assert_called_once_with("dummy.md", "w")
    m_open().write.assert_called_once()
    mock_db_client.init_pool.assert_called_once()
    mock_db_client.close_pool.assert_called_once()
