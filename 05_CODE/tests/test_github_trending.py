"""
Tests for scheduler/fetchers/github_trending.py
================================================
Authorized by: ANTIGRAVITY_PROTOCOL.md, Rule 3 (Testing Requirements)

Rules applied:
    - httpx.Client.get is fully mocked — no real HTTP calls
    - Each test tests one behavior
    - Naming: test_{what}_{condition}_{expected}
"""

import os
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

import sys
SCHEDULER_DIR = os.path.join(os.path.dirname(__file__), "..", "scheduler")
sys.path.insert(0, os.path.abspath(SCHEDULER_DIR))

from fetchers import github_trending
from fetchers.github_trending import (
    _canonicalize_url,
    _parse_date,
    _normalize_item,
)
from schemas.opportunity import OpportunityRecord


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_repo_item(
    full_name="user/blazing-fast-llm",
    html_url="https://github.com/user/blazing-fast-llm",
    description="A blazing fast LLM server written in Rust.",
    language="Rust",
    stargazers_count=5000,
    created_at="2026-07-01T12:00:00Z",
    topics=None,
    repo_id=12345,
    forks_count=200,
    watchers_count=5000,
) -> dict:
    """Create a mock GitHub repository item dictionary."""
    return {
        "full_name": full_name,
        "html_url": html_url,
        "description": description,
        "language": language,
        "stargazers_count": stargazers_count,
        "created_at": created_at,
        "topics": topics or ["llm", "server"],
        "id": repo_id,
        "forks_count": forks_count,
        "watchers_count": watchers_count,
    }


def make_mock_response(status_code=200, json_data=None):
    """Create a mock httpx.Response."""
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    if status_code == 200:
        mock_resp.json.return_value = json_data or {"items": []}
    else:
        # For non-200, raise_for_status would normally raise, simulate this behavior
        mock_resp.raise_for_status.side_effect = Exception(f"HTTP {status_code}")
    return mock_resp


# ---------------------------------------------------------------------------
# fetch() — top-level behavior
# ---------------------------------------------------------------------------

@patch("fetchers.github_trending.httpx.Client")
def test_fetch_returns_empty_list_on_network_failure(mock_client_cls):
    mock_client = mock_client_cls.return_value.__enter__.return_value
    mock_client.get.side_effect = Exception("Connection Timeout")
    
    result = github_trending.fetch()
    assert result == []


@patch("fetchers.github_trending.httpx.Client")
def test_fetch_returns_empty_list_on_403_rate_limit(mock_client_cls):
    mock_client = mock_client_cls.return_value.__enter__.return_value
    mock_client.get.return_value = make_mock_response(status_code=403)
    
    result = github_trending.fetch()
    assert result == []


@patch("fetchers.github_trending.httpx.Client")
def test_fetch_returns_empty_list_when_no_items(mock_client_cls):
    mock_client = mock_client_cls.return_value.__enter__.return_value
    mock_client.get.return_value = make_mock_response(json_data={"items": []})
    
    result = github_trending.fetch()
    assert result == []


@patch("fetchers.github_trending.httpx.Client")
def test_fetch_returns_list_of_opportunity_records(mock_client_cls):
    mock_client = mock_client_cls.return_value.__enter__.return_value
    items = [make_repo_item(), make_repo_item(full_name="user/repo2", html_url="https://github.com/user/repo2")]
    mock_client.get.return_value = make_mock_response(json_data={"items": items})
    
    result = github_trending.fetch()
    assert len(result) == 2
    assert all(isinstance(r, OpportunityRecord) for r in result)


@patch("fetchers.github_trending.httpx.Client")
def test_fetch_skips_bad_entry_and_continues(mock_client_cls):
    mock_client = mock_client_cls.return_value.__enter__.return_value
    good_item = make_repo_item()
    bad_item = make_repo_item(description=None) # Will be skipped
    mock_client.get.return_value = make_mock_response(json_data={"items": [bad_item, good_item]})
    
    result = github_trending.fetch()
    assert len(result) == 1
    assert result[0].title == "user/blazing-fast-llm"


@patch("fetchers.github_trending.httpx.Client")
def test_fetch_caps_at_max_items(mock_client_cls):
    mock_client = mock_client_cls.return_value.__enter__.return_value
    many_items = [
        make_repo_item(
            full_name=f"user/repo{i}",
            html_url=f"https://github.com/user/repo{i}"
        )
        for i in range(100)
    ]
    mock_client.get.return_value = make_mock_response(json_data={"items": many_items})
    
    result = github_trending.fetch()
    assert len(result) <= github_trending.MAX_ITEMS


@patch("fetchers.github_trending.httpx.Client")
def test_fetch_result_passes_validation(mock_client_cls):
    mock_client = mock_client_cls.return_value.__enter__.return_value
    mock_client.get.return_value = make_mock_response(json_data={"items": [make_repo_item()]})
    
    result = github_trending.fetch()
    assert len(result) == 1
    result[0].validate()


@patch("fetchers.github_trending.httpx.Client")
def test_fetch_uses_github_token_when_available(mock_client_cls):
    mock_client = mock_client_cls.return_value.__enter__.return_value
    mock_client.get.return_value = make_mock_response(json_data={"items": []})
    
    with patch.dict(os.environ, {"GITHUB_TOKEN": "secret_token"}):
        github_trending.fetch()
        
    call_args = mock_client.get.call_args
    assert call_args is not None
    headers = call_args.kwargs.get("headers", {})
    assert headers.get("Authorization") == "token secret_token"


@patch("fetchers.github_trending.httpx.Client")
def test_fetch_works_without_github_token(mock_client_cls):
    mock_client = mock_client_cls.return_value.__enter__.return_value
    mock_client.get.return_value = make_mock_response(json_data={"items": []})
    
    with patch.dict(os.environ, {}, clear=True):
        github_trending.fetch()
        
    call_args = mock_client.get.call_args
    headers = call_args.kwargs.get("headers", {})
    assert "Authorization" not in headers


# ---------------------------------------------------------------------------
# URL and Date Helpers
# ---------------------------------------------------------------------------

def test_canonicalize_url_lowercases_and_strips():
    result = _canonicalize_url("HTTPS://github.com/User/Repo/ ")
    assert result == "https://github.com/user/repo"


def test_parse_date_returns_utc_datetime_from_iso8601():
    result = _parse_date("2026-07-01T12:00:00Z")
    assert isinstance(result, datetime)
    assert result.tzinfo is not None
    assert result.year == 2026
    assert result.month == 7
    assert result.day == 1


def test_parse_date_falls_back_to_now_on_empty():
    result = _parse_date("")
    assert isinstance(result, datetime)
    assert result.tzinfo is not None


def test_parse_date_falls_back_to_now_on_invalid():
    result = _parse_date("not-a-date")
    assert isinstance(result, datetime)
    assert result.tzinfo is not None


# ---------------------------------------------------------------------------
# _normalize_item()
# ---------------------------------------------------------------------------

def test_normalize_item_returns_none_for_missing_description():
    item = make_repo_item(description=None)
    assert _normalize_item(item) is None

    item2 = make_repo_item(description="")
    assert _normalize_item(item2) is None


def test_normalize_item_returns_none_for_missing_language():
    item = make_repo_item(language=None)
    assert _normalize_item(item) is None


def test_normalize_item_returns_none_for_insufficient_stars():
    item = make_repo_item(stargazers_count=50) # MIN_STARS is 100
    assert _normalize_item(item) is None


def test_normalize_item_returns_none_for_missing_url():
    item = make_repo_item(html_url="")
    assert _normalize_item(item) is None


def test_normalize_item_sets_tool_and_use():
    item = make_repo_item()
    record = _normalize_item(item)
    assert record is not None
    assert record.opportunity_type == "tool"
    assert record.actionability_tier == "use"
    assert record.source == "github"


def test_normalize_item_includes_language_in_tags():
    item = make_repo_item(language="Rust", topics=["llm"])
    record = _normalize_item(item)
    assert record is not None
    assert "rust" in record.tags
    assert "llm" in record.tags


def test_normalize_item_populates_raw_metadata():
    item = make_repo_item(language="Go", stargazers_count=1000, forks_count=150, watchers_count=250)
    record = _normalize_item(item)
    assert record is not None
    meta = record.raw_metadata
    assert meta["language"] == "Go"
    assert meta["stars"] == 1000
    assert meta["forks"] == 150
    assert meta["watchers"] == 250


def test_normalize_item_handles_unexpected_exceptions():
    # Force an exception by passing something that breaks dict.get
    assert _normalize_item(["not", "a", "dict"]) is None
