"""
Tests for scheduler/fetchers/arxiv.py
======================================
Authorized by: ANTIGRAVITY_PROTOCOL.md, Rule 3 (Testing Requirements)

Rules applied:
    - feedparser.parse is fully mocked — no real HTTP calls
    - Each test tests one behavior
    - Naming: test_{what}_{condition}_{expected}

Run with:
    pytest 05_CODE/tests/test_arxiv.py -v
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

import sys
import os
SCHEDULER_DIR = os.path.join(os.path.dirname(__file__), "..", "scheduler")
sys.path.insert(0, os.path.abspath(SCHEDULER_DIR))

from fetchers import arxiv as arxiv_fetcher
from fetchers.arxiv import (
    _classify,
    _canonicalize_url,
    _strip_html,
    _clean_title,
    _parse_published_at,
    _extract_tags,
    _extract_tech_stack,
    _map_domains,
    _normalize_entry,
    CODE_KEYWORDS,
    DATASET_KEYWORDS,
)
from schemas.opportunity import OpportunityRecord


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_entry(
    title="Test Paper: Attention and Beyond",
    link="https://arxiv.org/abs/2401.00001",
    summary="We study attention mechanisms in large language models.",
    published_parsed=(2026, 7, 4, 8, 0, 0, 0, 185, 0),
    tags=None,
    author="Smith, J.; Doe, A.",
    entry_id="https://arxiv.org/abs/2401.00001",
) -> MagicMock:
    """Create a mock feedparser entry."""
    entry = MagicMock()
    entry.title = title
    entry.link = link
    entry.summary = summary
    entry.published_parsed = published_parsed
    entry.tags = tags if tags is not None else []
    entry.author = author
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
    """fetch() returns [] and does not raise when feedparser.parse raises."""
    with patch("fetchers.arxiv.feedparser.parse", side_effect=Exception("timeout")):
        result = arxiv_fetcher.fetch()
    assert result == []


def test_fetch_returns_empty_list_when_no_entries():
    """fetch() returns [] when the RSS feed contains no entries."""
    with patch("fetchers.arxiv.feedparser.parse", return_value=make_feed(entries=[])):
        result = arxiv_fetcher.fetch()
    assert result == []


def test_fetch_returns_list_of_opportunity_records():
    """fetch() returns a list of OpportunityRecord instances for valid entries."""
    entries = [make_entry(), make_entry(
        title="Second Paper",
        link="https://arxiv.org/abs/2401.00002",
        entry_id="https://arxiv.org/abs/2401.00002",
    )]
    with patch("fetchers.arxiv.feedparser.parse", return_value=make_feed(entries=entries)):
        result = arxiv_fetcher.fetch()
    assert len(result) == 2
    assert all(isinstance(r, OpportunityRecord) for r in result)


def test_fetch_skips_bad_entry_and_continues():
    """fetch() skips entries that fail normalization without stopping."""
    good_entry = make_entry()
    bad_entry = make_entry(title="", link="")  # will be skipped — no title
    with patch("fetchers.arxiv.feedparser.parse",
               return_value=make_feed(entries=[bad_entry, good_entry])):
        result = arxiv_fetcher.fetch()
    assert len(result) == 1
    assert result[0].title == "Test Paper: Attention and Beyond"


def test_fetch_handles_bozo_feed_gracefully():
    """fetch() continues processing even when feedparser reports a malformed feed."""
    entries = [make_entry()]
    feed = make_feed(
        entries=entries,
        bozo=True,
        bozo_exception=Exception("not well-formed"),
    )
    with patch("fetchers.arxiv.feedparser.parse", return_value=feed):
        result = arxiv_fetcher.fetch()
    assert len(result) == 1


def test_fetch_caps_at_max_items():
    """fetch() processes at most MAX_ITEMS entries from the feed."""
    many_entries = [
        make_entry(
            title=f"Paper {i}",
            link=f"https://arxiv.org/abs/240{i:05d}",
            entry_id=f"https://arxiv.org/abs/240{i:05d}",
        )
        for i in range(100)
    ]
    with patch("fetchers.arxiv.feedparser.parse",
               return_value=make_feed(entries=many_entries)):
        result = arxiv_fetcher.fetch()
    assert len(result) <= arxiv_fetcher.MAX_ITEMS


def test_fetch_result_passes_validation():
    """fetch() results pass OpportunityRecord.validate() without error."""
    entries = [make_entry()]
    with patch("fetchers.arxiv.feedparser.parse", return_value=make_feed(entries=entries)):
        result = arxiv_fetcher.fetch()
    assert len(result) == 1
    result[0].validate()  # Should not raise


def test_fetch_sets_source_to_arxiv():
    """fetch() sets source='arxiv' on every returned record."""
    entries = [make_entry()]
    with patch("fetchers.arxiv.feedparser.parse", return_value=make_feed(entries=entries)):
        result = arxiv_fetcher.fetch()
    assert all(r.source == "arxiv" for r in result)


# ---------------------------------------------------------------------------
# _classify() — opportunity type promotion
# ---------------------------------------------------------------------------

def test_classify_returns_tool_and_use_for_code_keyword():
    """_classify() returns ('tool', 'use') when CODE_KEYWORDS appear in text."""
    opp_type, tier = _classify("New Model", "We release our code at github.com/user/repo")
    assert opp_type == "tool"
    assert tier == "use"


def test_classify_returns_dataset_and_use_for_dataset_keyword():
    """_classify() returns ('dataset', 'use') when DATASET_KEYWORDS appear."""
    opp_type, tier = _classify("New Benchmark", "We introduce a benchmark for NLP evaluation")
    assert opp_type == "dataset"
    assert tier == "use"


def test_classify_returns_paper_and_learn_when_no_keywords():
    """_classify() returns ('paper', 'learn') when no promotion keywords match."""
    opp_type, tier = _classify("A Survey of Attention", "We survey existing attention mechanisms.")
    assert opp_type == "paper"
    assert tier == "learn"


def test_classify_code_takes_priority_over_dataset():
    """_classify() returns 'tool' when both CODE_KEYWORDS and DATASET_KEYWORDS match."""
    opp_type, tier = _classify(
        "Dataset Release",
        "We release our code and dataset at github.com/user/repo"
    )
    assert opp_type == "tool"  # code_keywords checked first


def test_classify_is_case_insensitive():
    """_classify() matches keywords regardless of case."""
    opp_type, tier = _classify("GREAT PAPER", "WE RELEASE OUR OPEN-SOURCE implementation")
    assert opp_type == "tool"


# ---------------------------------------------------------------------------
# _canonicalize_url()
# ---------------------------------------------------------------------------

def test_canonicalize_url_strips_version_suffix():
    """_canonicalize_url() removes version suffix like 'v2' from Arxiv URLs."""
    result = _canonicalize_url("https://arxiv.org/abs/2401.00001v2")
    assert result == "https://arxiv.org/abs/2401.00001"


def test_canonicalize_url_lowercases_url():
    """_canonicalize_url() lowercases the entire URL."""
    result = _canonicalize_url("HTTPS://Arxiv.org/abs/2401.00001")
    assert result == "https://arxiv.org/abs/2401.00001"


def test_canonicalize_url_removes_trailing_slash():
    """_canonicalize_url() strips trailing slashes."""
    result = _canonicalize_url("https://arxiv.org/abs/2401.00001/")
    assert result == "https://arxiv.org/abs/2401.00001"


def test_canonicalize_url_is_idempotent():
    """_canonicalize_url() applied twice gives the same result."""
    url = "https://arxiv.org/abs/2401.00001v3"
    once = _canonicalize_url(url)
    twice = _canonicalize_url(once)
    assert once == twice


# ---------------------------------------------------------------------------
# _strip_html()
# ---------------------------------------------------------------------------

def test_strip_html_removes_paragraph_tags():
    """_strip_html() removes <p> tags from text."""
    result = _strip_html("<p>This is a summary.</p>")
    assert "<p>" not in result
    assert "This is a summary." in result


def test_strip_html_removes_italic_tags():
    """_strip_html() removes <i> tags."""
    result = _strip_html("The model <i>significantly</i> improves performance.")
    assert "<i>" not in result
    assert "significantly" in result


def test_strip_html_handles_plain_text():
    """_strip_html() returns plain text unchanged."""
    result = _strip_html("No HTML here.")
    assert result == "No HTML here."


# ---------------------------------------------------------------------------
# _clean_title()
# ---------------------------------------------------------------------------

def test_clean_title_removes_trailing_period():
    """_clean_title() strips trailing period from Arxiv title."""
    result = _clean_title("FlashAttention: Fast Memory-Efficient Exact Attention.")
    assert not result.endswith(".")


def test_clean_title_collapses_whitespace():
    """_clean_title() collapses multiple spaces into one."""
    result = _clean_title("A  Paper   With  Spaces")
    assert result == "A Paper With Spaces"


def test_clean_title_strips_surrounding_whitespace():
    """_clean_title() strips leading and trailing whitespace."""
    result = _clean_title("  Attention Mechanisms  ")
    assert result == "Attention Mechanisms"


# ---------------------------------------------------------------------------
# _parse_published_at()
# ---------------------------------------------------------------------------

def test_parse_published_at_returns_utc_datetime_from_struct():
    """_parse_published_at() returns a UTC-aware datetime from published_parsed."""
    entry = make_entry(published_parsed=(2026, 7, 4, 8, 0, 0, 0, 185, 0))
    result = _parse_published_at(entry)
    assert isinstance(result, datetime)
    assert result.tzinfo is not None
    assert result.year == 2026
    assert result.month == 7
    assert result.day == 4


def test_parse_published_at_falls_back_to_now_when_missing():
    """_parse_published_at() returns UTC now when published_parsed is None."""
    entry = make_entry(published_parsed=None)
    before = datetime.now(timezone.utc)
    result = _parse_published_at(entry)
    after = datetime.now(timezone.utc)
    assert before <= result <= after


# ---------------------------------------------------------------------------
# _extract_tags()
# ---------------------------------------------------------------------------

def test_extract_tags_returns_subject_codes():
    """_extract_tags() returns the term from each feedparser tag object."""
    entry = make_entry(tags=[make_tag("cs.AI"), make_tag("cs.LG")])
    result = _extract_tags(entry)
    assert "cs.AI" in result
    assert "cs.LG" in result


def test_extract_tags_returns_empty_list_when_no_tags():
    """_extract_tags() returns [] when entry has no tags."""
    entry = make_entry(tags=[])
    result = _extract_tags(entry)
    assert result == []


# ---------------------------------------------------------------------------
# _extract_tech_stack()
# ---------------------------------------------------------------------------

def test_extract_tech_stack_detects_pytorch():
    """_extract_tech_stack() detects PyTorch from text."""
    result = _extract_tech_stack("We implemented our model using PyTorch.")
    assert "pytorch" in result


def test_extract_tech_stack_detects_jax():
    """_extract_tech_stack() detects JAX from text."""
    result = _extract_tech_stack("Experiments conducted using JAX and Flax.")
    assert "jax" in result


def test_extract_tech_stack_returns_empty_for_no_matches():
    """_extract_tech_stack() returns [] when no tech stack keywords match."""
    result = _extract_tech_stack("We use abstract mathematical notation.")
    assert result == []


# ---------------------------------------------------------------------------
# _map_domains()
# ---------------------------------------------------------------------------

def test_map_domains_maps_cs_ai_to_ai():
    """_map_domains() maps 'cs.AI' to 'ai'."""
    result = _map_domains(["cs.AI"])
    assert "ai" in result


def test_map_domains_maps_cs_lg_to_ml():
    """_map_domains() maps 'cs.LG' to 'ml'."""
    result = _map_domains(["cs.LG"])
    assert "ml" in result


def test_map_domains_deduplicates():
    """_map_domains() returns each domain at most once."""
    result = _map_domains(["cs.AI", "cs.CL"])  # both map to "ai"
    assert result.count("ai") == 1


def test_map_domains_returns_empty_for_unknown_codes():
    """_map_domains() returns [] for subject codes not in the domain map."""
    result = _map_domains(["cs.XY", "stat.ZZ"])
    assert result == []


# ---------------------------------------------------------------------------
# _normalize_entry() — edge cases
# ---------------------------------------------------------------------------

def test_normalize_entry_returns_none_for_empty_title():
    """_normalize_entry() returns None when entry has no title."""
    entry = make_entry(title="")
    result = _normalize_entry(entry)
    assert result is None


def test_normalize_entry_returns_none_for_missing_url():
    """_normalize_entry() returns None when entry link is empty."""
    entry = make_entry(link="")
    result = _normalize_entry(entry)
    assert result is None


def test_normalize_entry_returns_none_on_unexpected_exception():
    """_normalize_entry() returns None instead of raising on unexpected error."""
    bad_entry = MagicMock()
    bad_entry.title = "Good Title"
    bad_entry.link = "https://arxiv.org/abs/0000"
    # Make summary access raise
    type(bad_entry).summary = property(flaw := lambda self: (_ for _ in ()).throw(RuntimeError("boom")))
    result = _normalize_entry(bad_entry)
    assert result is None


def test_normalize_entry_stores_authors_in_raw_metadata():
    """_normalize_entry() includes author info in raw_metadata."""
    entry = make_entry(author="Hinton, G.; LeCun, Y.")
    result = _normalize_entry(entry)
    assert result is not None
    assert result.raw_metadata["authors"] == "Hinton, G.; LeCun, Y."
