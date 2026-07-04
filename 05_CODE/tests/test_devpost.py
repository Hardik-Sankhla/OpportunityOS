"""
Tests for scheduler/fetchers/devpost.py
========================================
Authorized by: ANTIGRAVITY_PROTOCOL.md, Rule 3 (Testing Requirements)

Rules applied:
    - feedparser.parse is fully mocked — no real HTTP calls
    - Each test tests one behavior
    - Naming: test_{what}_{condition}_{expected}
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

import sys
import os
SCHEDULER_DIR = os.path.join(os.path.dirname(__file__), "..", "scheduler")
sys.path.insert(0, os.path.abspath(SCHEDULER_DIR))

from fetchers import devpost as devpost_fetcher
from fetchers.devpost import (
    _canonicalize_url,
    _strip_html,
    _clean_title,
    _parse_published_at,
    _extract_tags,
    _extract_tech_stack,
    _normalize_entry,
)
from schemas.opportunity import OpportunityRecord


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_entry(
    title="Global AI Hackathon",
    link="https://devpost.com/software/global-ai",
    summary="Build the next gen AI apps.",
    published_parsed=(2026, 7, 4, 8, 0, 0, 0, 185, 0),
    tags=None,
    entry_id="https://devpost.com/software/global-ai",
) -> MagicMock:
    """Create a mock feedparser entry."""
    entry = MagicMock()
    entry.title = title
    entry.link = link
    entry.summary = summary
    entry.published_parsed = published_parsed
    entry.tags = tags if tags is not None else []
    entry.id = entry_id
    return entry


def make_feed(entries=None, bozo=False, bozo_exception=None) -> MagicMock:
    """Create a mock feedparser result."""
    feed = MagicMock()
    feed.entries = entries or []
    feed.bozo = bozo
    feed.bozo_exception = bozo_exception
    return feed


def make_tag(term: str) -> MagicMock:
    tag = MagicMock()
    tag.term = term
    return tag


# ---------------------------------------------------------------------------
# fetch() — top-level behavior
# ---------------------------------------------------------------------------

def test_fetch_returns_empty_list_on_network_failure():
    with patch("fetchers.devpost.feedparser.parse", side_effect=Exception("timeout")):
        result = devpost_fetcher.fetch()
    assert result == []


def test_fetch_returns_empty_list_when_no_entries():
    with patch("fetchers.devpost.feedparser.parse", return_value=make_feed(entries=[])):
        result = devpost_fetcher.fetch()
    assert result == []


def test_fetch_returns_list_of_opportunity_records():
    entries = [make_entry(), make_entry(
        title="Web3 Hack",
        link="https://devpost.com/software/web3-hack",
        entry_id="https://devpost.com/software/web3-hack",
    )]
    with patch("fetchers.devpost.feedparser.parse", return_value=make_feed(entries=entries)):
        result = devpost_fetcher.fetch()
    assert len(result) == 2
    assert all(isinstance(r, OpportunityRecord) for r in result)


def test_fetch_skips_bad_entry_and_continues():
    good_entry = make_entry()
    bad_entry = make_entry(title="", link="")
    with patch("fetchers.devpost.feedparser.parse",
               return_value=make_feed(entries=[bad_entry, good_entry])):
        result = devpost_fetcher.fetch()
    assert len(result) == 1
    assert result[0].title == "Global AI Hackathon"


def test_fetch_handles_bozo_feed_gracefully():
    entries = [make_entry()]
    feed = make_feed(
        entries=entries,
        bozo=True,
        bozo_exception=Exception("not well-formed"),
    )
    with patch("fetchers.devpost.feedparser.parse", return_value=feed):
        result = devpost_fetcher.fetch()
    assert len(result) == 1


def test_fetch_caps_at_max_items():
    many_entries = [
        make_entry(
            title=f"Hack {i}",
            link=f"https://devpost.com/software/hack-{i:05d}",
            entry_id=f"https://devpost.com/software/hack-{i:05d}",
        )
        for i in range(100)
    ]
    with patch("fetchers.devpost.feedparser.parse",
               return_value=make_feed(entries=many_entries)):
        result = devpost_fetcher.fetch()
    assert len(result) <= devpost_fetcher.MAX_ITEMS


def test_fetch_result_passes_validation():
    entries = [make_entry()]
    with patch("fetchers.devpost.feedparser.parse", return_value=make_feed(entries=entries)):
        result = devpost_fetcher.fetch()
    assert len(result) == 1
    result[0].validate()  # Should not raise


def test_fetch_sets_source_to_devpost_and_tier_compete():
    entries = [make_entry()]
    with patch("fetchers.devpost.feedparser.parse", return_value=make_feed(entries=entries)):
        result = devpost_fetcher.fetch()
    assert all(r.source == "devpost" for r in result)
    assert all(r.opportunity_type == "hackathon" for r in result)
    assert all(r.actionability_tier == "compete" for r in result)


# ---------------------------------------------------------------------------
# URL and Content Helpers
# ---------------------------------------------------------------------------

def test_canonicalize_url_strips_query_parameters():
    result = _canonicalize_url("https://devpost.com/software/global-ai?ref_content=default&ref_feature=in-app")
    assert result == "https://devpost.com/software/global-ai"


def test_canonicalize_url_lowercases():
    result = _canonicalize_url("HTTPS://DevPost.COM/Software/Hack")
    assert result == "https://devpost.com/software/hack"


def test_strip_html_removes_tags():
    result = _strip_html("<p>Build <b>cool</b> stuff.</p>")
    assert "cool" in result
    assert "<p>" not in result


def test_clean_title_collapses_whitespace():
    result = _clean_title("  Global   Hackathon  ")
    assert result == "Global Hackathon"


def test_parse_published_at_returns_utc_datetime_from_struct():
    entry = make_entry(published_parsed=(2026, 7, 4, 8, 0, 0, 0, 185, 0))
    result = _parse_published_at(entry)
    assert isinstance(result, datetime)
    assert result.year == 2026


def test_parse_published_at_falls_back_to_now():
    entry = make_entry(published_parsed=None)
    result = _parse_published_at(entry)
    assert isinstance(result, datetime)


def test_extract_tags_lowercases():
    entry = make_entry(tags=[make_tag("Machine Learning"), make_tag("AI")])
    result = _extract_tags(entry)
    assert "machine learning" in result
    assert "ai" in result


def test_extract_tech_stack_detects_llm_and_web3():
    result = _extract_tech_stack("Use an LLM or deploy on Ethereum.")
    assert "llm" in result
    assert "web3" in result


def test_normalize_entry_returns_none_for_missing_url():
    entry = make_entry(link="")
    assert _normalize_entry(entry) is None


def test_normalize_entry_handles_unexpected_exceptions():
    bad_entry = MagicMock()
    bad_entry.title = "Good"
    bad_entry.link = "http://devpost.com/software/test"
    type(bad_entry).summary = property(flaw := lambda self: (_ for _ in ()).throw(ValueError("nope")))
    assert _normalize_entry(bad_entry) is None
